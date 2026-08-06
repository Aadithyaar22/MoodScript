"""
A/B tests candidate Groq-hosted LLMs against the current production model
(llama-3.3-70b-versatile) using the EXACT prompt-construction logic from
models/response.py (imported directly, not reimplemented) — only the `model=`
string passed to the completion call varies. This isolates the comparison to
"does a different model produce a better response to the same prompt," not
"did we also change the prompt."

Scores each response on objectively-checkable rule adherence (banned openers,
sentence-count limit, no bullet points) and a rough content-specificity proxy
(does the response mention any of the hand-tagged key entities from the input),
plus wall-clock latency and prints full transcripts for qualitative reading —
"good therapist response" is ultimately a judgment call, not a metric.

Usage:
    python3 eval_llm_ab.py --models llama-3.3-70b-versatile,openai/gpt-oss-120b --out results/llm_ab.json
"""
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

sys.path.insert(0, str(Path(__file__).parent.parent))
from models.response import PERSONAS, RULES, BANNED_OPENERS, _pick_angle, _long_term_block  # noqa: E402

load_dotenv(Path(__file__).parent.parent / ".env")

# (user_text, emotion, confidence, key_entities) — key_entities are hand-tagged specific
# details a genuinely attentive response should plausibly reference, used as a rough,
# imperfect proxy for "did it engage with the specifics, not just the emotion label."
TEST_CASES = [
    ("My manager Sarah pulled me into a meeting today and told me the Q3 project I led "
     "for eight months is getting cancelled. I don't even know what to say to my team tomorrow.",
     "sad", 0.85, ["Sarah", "Q3", "project", "team", "cancel"]),

    ("My little brother Max got into the college he's wanted since he was twelve. I drove "
     "four hours to be there when the letter came. I've never seen him cry like that.",
     "happy", 0.9, ["Max", "college", "letter", "drove", "brother"]),

    ("I found out my dad has been lying to my mom about the debt for two years. Found the "
     "statements in a drawer by accident. I don't know if I should say something.",
     "fearful", 0.75, ["dad", "mom", "debt", "drawer", "lying"]),

    ("Third time this month my flight got delayed for the same client trip to Chicago. "
     "I missed my daughter's recital again because of it.",
     "angry", 0.88, ["flight", "Chicago", "daughter", "recital", "delayed"]),
]

MODEL_LABELS_INTERNAL = {}  # populated at runtime for report labeling

# Reasoning models (e.g. gpt-oss) spend completion tokens on a hidden reasoning channel
# before producing visible output — the production max_tokens=260 (tuned for the
# non-reasoning llama-3.3) leaves no room left for an actual answer and silently returns
# empty content. Give reasoning models real headroom instead.
def max_tokens_for(model: str) -> int:
    return 1500 if "gpt-oss" in model else 260


def build_prompt(user_text, emotion, confidence):
    persona = PERSONAS[0]
    angle = _pick_angle(emotion, confidence)
    system_prompt = f"{persona}{_long_term_block('')}\n\n{RULES}"
    user_prompt = f"""Someone shared how they're feeling. Emotion: {emotion} ({confidence:.0%}).

How to approach this response:
{angle}

Opening instruction (critical — follow this exactly):
Start with a direct, personal statement — no preamble, no 'there's something special about...'

They wrote:
\"\"\"{user_text[:800]}\"\"\"

Write your response as Aria. One person, one moment, one message. Make it feel completely unrepeatable."""
    return system_prompt, user_prompt


def score_response(text, key_entities):
    banned = any(text.strip().startswith(b) for b in BANNED_OPENERS)
    sentence_count = len(re.findall(r"[.!?]+(?:\s|$)", text))
    has_bullets = bool(re.search(r"^\s*[-*•]\s", text, re.MULTILINE))
    entity_hits = sum(1 for e in key_entities if e.lower() in text.lower())
    return {
        "banned_opener": banned,
        "sentence_count": sentence_count,
        "within_length_limit": sentence_count <= 5,
        "has_bullets": has_bullets,
        "entity_hits": entity_hits,
        "entity_hit_rate": round(entity_hits / len(key_entities), 2) if key_entities else None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", required=True, help="comma-separated Groq model IDs")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    models = [m.strip() for m in args.models.split(",")]

    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    results = {m: [] for m in models}

    for text, emotion, confidence, entities in TEST_CASES:
        system_prompt, user_prompt = build_prompt(text, emotion, confidence)
        print(f"\n{'='*80}\nCASE: {text[:70]}...\n{'='*80}")
        for model in models:
            start = time.time()
            try:
                completion = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "system", "content": system_prompt},
                              {"role": "user", "content": user_prompt}],
                    max_tokens=max_tokens_for(model), temperature=1.0, top_p=0.92,
                    frequency_penalty=0.6, presence_penalty=0.4,
                )
                response_text = (completion.choices[0].message.content or "").strip()
                elapsed = time.time() - start
                reasoning_tokens = getattr(completion.usage.completion_tokens_details, "reasoning_tokens", None) \
                    if completion.usage and completion.usage.completion_tokens_details else None
                score = score_response(response_text, entities)
                results[model].append({"input": text, "response": response_text,
                                        "elapsed_seconds": round(elapsed, 2),
                                        "completion_tokens": completion.usage.completion_tokens if completion.usage else None,
                                        "reasoning_tokens": reasoning_tokens, **score})
                print(f"\n--- {model} ({elapsed:.1f}s) ---\n{response_text}\n[{score}]")
            except Exception as e:
                print(f"\n--- {model} ERROR: {e} ---")
                results[model].append({"input": text, "error": str(e)})

    print(f"\n\n{'='*80}\nSUMMARY\n{'='*80}")
    print(f"{'MODEL':<35}{'AVG_LATENCY':<14}{'BANNED_OPENER':<16}{'OVER_LENGTH':<14}{'BULLETS':<10}{'AVG_ENTITY_HIT':<16}")
    for model in models:
        rows = [r for r in results[model] if "error" not in r]
        if not rows:
            print(f"{model:<35}ALL ERRORED")
            continue
        avg_lat = sum(r["elapsed_seconds"] for r in rows) / len(rows)
        banned_n = sum(r["banned_opener"] for r in rows)
        over_len_n = sum(not r["within_length_limit"] for r in rows)
        bullets_n = sum(r["has_bullets"] for r in rows)
        avg_entity = sum(r["entity_hit_rate"] or 0 for r in rows) / len(rows)
        print(f"{model:<35}{avg_lat:<14.2f}{banned_n:<16}{over_len_n:<14}{bullets_n:<10}{avg_entity:<16.2f}")

    with open(args.out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nFull transcripts saved to {args.out}")


if __name__ == "__main__":
    main()
