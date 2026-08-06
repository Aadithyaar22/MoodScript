"""Validates the two-pass extraction+response split (models/response.py) by running the
real ResponseEngine.generate() on the same 4 test cases used in eval_llm_ab.py, scoring
content-specificity the same way, for a direct before/after comparison — before: 0.35 avg
entity-hit-rate (see results/llm_ab_gptoss.json, llama-3.3-70b-versatile column)."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from models.response import ResponseEngine  # noqa: E402

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


def score(text, key_entities):
    hits = sum(1 for e in key_entities if e.lower() in text.lower())
    return hits, round(hits / len(key_entities), 2)


async def main():
    engine = ResponseEngine()
    rates = []
    for text, emotion, confidence, entities in TEST_CASES:
        key_facts = await engine._extract_key_facts(text)
        response, _ = await engine.generate(emotion, confidence, text, None, None)
        hits, rate = score(response, entities)
        rates.append(rate)
        print(f"\n{'='*80}\nINPUT: {text[:70]}...")
        print(f"EXTRACTED FACTS: {key_facts}")
        print(f"RESPONSE: {response}")
        print(f"entity_hits: {hits}/{len(entities)} = {rate}")

    print(f"\n\nAVG entity_hit_rate (with two-pass extraction): {sum(rates)/len(rates):.2f}")
    print("AVG entity_hit_rate (baseline, no extraction, from eval_llm_ab.py): 0.35")


if __name__ == "__main__":
    asyncio.run(main())
