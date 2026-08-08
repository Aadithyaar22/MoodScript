"""
A/B tests Claude Sonnet 5 and GPT-4o against the current production model
(llama-3.3-70b-versatile on Groq), using the exact same prompt-construction logic and
test cases as eval_llm_ab.py — only the provider/model varies. Same scoring: rule
adherence (banned openers, length, bullets) + entity-hit-rate content-specificity proxy,
plus real measured latency and token usage for a real cost comparison.

Usage:
    python3 eval_llm_ab_external.py --out results/llm_ab_external.json
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).parent.parent))
from models.response import PERSONAS, _pick_angle, _long_term_block  # noqa: E402
from eval_llm_ab import TEST_CASES, build_prompt, score_response  # noqa: E402

load_dotenv(Path(__file__).parent.parent / ".env")

# $ per million tokens, input/output — verified against each provider's official pricing
# page directly (not model-card claims), see commit message for sources.
PRICING = {
    "claude-sonnet-5": (2.00, 10.00),
    "gpt-4o": (2.50, 10.00),
    "llama-3.3-70b-versatile": (0.59, 0.79),  # Groq, for reference — same as eval_llm_ab.py
}


def call_claude(client, system_prompt, user_prompt):
    start = time.time()
    resp = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=260,
        temperature=1.0,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    elapsed = time.time() - start
    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    return text, elapsed, resp.usage.input_tokens, resp.usage.output_tokens


def call_gpt4o(client, system_prompt, user_prompt):
    start = time.time()
    resp = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=260,
        temperature=1.0,
        messages=[{"role": "system", "content": system_prompt},
                  {"role": "user", "content": user_prompt}],
    )
    elapsed = time.time() - start
    text = (resp.choices[0].message.content or "").strip()
    return text, elapsed, resp.usage.prompt_tokens, resp.usage.completion_tokens


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    results = {"claude-sonnet-5": [], "gpt-4o": []}

    for text, emotion, confidence, entities in TEST_CASES:
        system_prompt, user_prompt = build_prompt(text, emotion, confidence)
        print(f"\n{'='*80}\nCASE: {text[:70]}...\n{'='*80}")

        for model, fn, client in [
            ("claude-sonnet-5", call_claude, anthropic_client),
            ("gpt-4o", call_gpt4o, openai_client),
        ]:
            try:
                response_text, elapsed, in_tok, out_tok = fn(client, system_prompt, user_prompt)
                score = score_response(response_text, entities)
                in_price, out_price = PRICING[model]
                cost = (in_tok * in_price + out_tok * out_price) / 1_000_000
                results[model].append({
                    "input": text, "response": response_text, "elapsed_seconds": round(elapsed, 2),
                    "input_tokens": in_tok, "output_tokens": out_tok, "cost_usd": round(cost, 6),
                    **score,
                })
                print(f"\n--- {model} ({elapsed:.1f}s, {out_tok} out tok, ${cost:.5f}) ---\n{response_text}\n[{score}]")
            except Exception as e:
                print(f"\n--- {model} ERROR: {e} ---")
                results[model].append({"input": text, "error": str(e)})

    print(f"\n\n{'='*80}\nSUMMARY (llama-3.3-70b-versatile baseline from eval_llm_ab.py: "
          f"0.82s avg, 113.5 avg completion tokens, ~$0.00009/response, 0.35 avg entity-hit-rate)\n{'='*80}")
    print(f"{'MODEL':<20}{'AVG_LATENCY':<14}{'AVG_OUT_TOK':<14}{'AVG_COST':<14}{'BANNED':<10}{'OVER_LEN':<10}{'AVG_ENTITY_HIT':<16}")
    for model, rows in results.items():
        ok = [r for r in rows if "error" not in r]
        if not ok:
            print(f"{model:<20}ALL ERRORED")
            continue
        avg_lat = sum(r["elapsed_seconds"] for r in ok) / len(ok)
        avg_tok = sum(r["output_tokens"] for r in ok) / len(ok)
        avg_cost = sum(r["cost_usd"] for r in ok) / len(ok)
        banned_n = sum(r["banned_opener"] for r in ok)
        over_len_n = sum(not r["within_length_limit"] for r in ok)
        avg_entity = sum(r["entity_hit_rate"] or 0 for r in ok) / len(ok)
        print(f"{model:<20}{avg_lat:<14.2f}{avg_tok:<14.1f}${avg_cost:<13.5f}{banned_n:<10}{over_len_n:<10}{avg_entity:<16.2f}")

    with open(args.out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nFull transcripts saved to {args.out}")


if __name__ == "__main__":
    main()
