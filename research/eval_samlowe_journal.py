"""Runs SamLowe/roberta-base-go_emotions (Ekman-mapped) against the same 49 hand-built
journal-style test cases the current model was validated on, to check whether its
GoEmotions benchmark win is a real general improvement or just home-turf advantage."""
import json

from transformers import pipeline

from eval_text_candidates import FINE_TO_UNIFIED

TESTS = json.load(open("/tmp/tests49.json"))

print("Loading SamLowe/roberta-base-go_emotions...")
clf = pipeline("text-classification", model="SamLowe/roberta-base-go_emotions", top_k=None, device=-1)

correct = 0
by_category = {}
rows = []
for text, expected, category in TESTS:
    preds = clf(text[:512])
    if preds and isinstance(preds[0], list):
        preds = preds[0]
    top = max(preds, key=lambda p: p["score"])
    got = FINE_TO_UNIFIED.get(top["label"].lower(), "neutral")
    ok = got == expected
    correct += ok
    by_category.setdefault(category, [0, 0])
    by_category[category][1] += 1
    by_category[category][0] += ok
    rows.append((ok, category, expected, got, top["score"], text))

print(f"{'OK':<4}{'CATEGORY':<10}{'EXPECTED':<12}{'GOT':<12}{'CONF':<7}TEXT")
for ok, category, expected, got, conf, text in rows:
    mark = " " if ok else "X"
    print(f"{mark:<4}{category:<10}{expected:<12}{got:<12}{conf:.2f}   {text[:70]}")

print(f"\nOverall: {correct}/{len(TESTS)} = {correct/len(TESTS)*100:.0f}%")
for cat, (c, t) in by_category.items():
    print(f"  {cat}: {c}/{t} = {c/t*100:.0f}%")
