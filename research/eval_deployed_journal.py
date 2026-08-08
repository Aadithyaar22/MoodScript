"""Runs the DEPLOYED text pipeline (j-hartmann + syntax-aware negation dampening)
against the same 49 journal-style cases used by eval_samlowe_journal.py.

Both scripts read research/data/journal_tests_49.json and report the same
breakdown, so the deployed model and any candidate are measured identically.
This is the comparison that justified keeping j-hartmann even though SamLowe
scores far higher on GoEmotions — GoEmotions is SamLowe's training distribution.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                                "services", "text_service"))

from text_model import TextEmotionModel  # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = json.load(open(os.path.join(_HERE, "data", "journal_tests_49.json")))

print("Loading deployed text pipeline...")
model = TextEmotionModel()

correct = 0
by_category = {}
rows = []
for case in TESTS:
    text, expected, category = case["text"], case["expected"], case["category"]
    got = model.predict(text)["dominant_emotion"]
    ok = got == expected
    correct += ok
    by_category.setdefault(category, [0, 0])
    by_category[category][1] += 1
    by_category[category][0] += ok
    rows.append((ok, category, expected, got, text))

print()
for ok, category, expected, got, text in rows:
    print(f"{'  ' if ok else 'X '}  {category:<9} {expected:<11} {got:<11} {text[:66]}")

print(f"\nOverall: {correct}/{len(TESTS)} = {correct/len(TESTS)*100:.0f}%")
for cat, (c, n) in by_category.items():
    print(f"  {cat}: {c}/{n} = {c/n*100:.0f}%")

out = os.path.join(_HERE, "results", "deployed_journal_49.json")
with open(out, "w") as f:
    json.dump({
        "model": "MoodScript deployed pipeline (j-hartmann + negation dampening)",
        "n_cases": len(TESTS),
        "overall_accuracy": correct / len(TESTS),
        "by_category": {k: {"correct": v[0], "n": v[1]} for k, v in by_category.items()},
        "rows": [{"correct": ok, "category": c, "expected": e, "predicted": g, "text": t}
                 for ok, c, e, g, t in rows],
    }, f, indent=2, ensure_ascii=False)
print(f"\nSaved to {out}")
