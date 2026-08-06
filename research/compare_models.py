"""Paired comparison of two eval_face_models.py output files on the same test set:
prints a side-by-side per-class table and runs McNemar's test on the paired
correct/incorrect outcomes to check the accuracy gap is statistically significant."""
import argparse
import json

from statsmodels.stats.contingency_tables import mcnemar

ap = argparse.ArgumentParser()
ap.add_argument("--a", required=True)
ap.add_argument("--b", required=True)
args = ap.parse_args()

a = json.load(open(args.a))
b = json.load(open(args.b))

print(f"{'CLASS':<12}{a['model']:<45}{b['model']:<45}")
for label in a["per_class"]:
    ra, rb = a["per_class"][label], b["per_class"][label]
    print(f"{label:<12}"
          f"P={ra['precision']*100:>5.1f} R={ra['recall']*100:>5.1f} F1={ra['f1-score']*100:>5.1f}{'':<20}"
          f"P={rb['precision']*100:>5.1f} R={rb['recall']*100:>5.1f} F1={rb['f1-score']*100:>5.1f}")

print(f"\nOverall accuracy: {a['model']} = {a['overall_accuracy']*100:.2f}%   {b['model']} = {b['overall_accuracy']*100:.2f}%")

# Paired McNemar's test: both correct, both wrong, a-right/b-wrong, a-wrong/b-right
preds_a = {r["idx"]: r for r in a["raw_predictions"]}
preds_b = {r["idx"]: r for r in b["raw_predictions"]}
both_right = a_right_b_wrong = a_wrong_b_right = both_wrong = 0
for idx in preds_a:
    ra, rb = preds_a[idx], preds_b[idx]
    a_correct = ra["pred"] == ra["true"]
    b_correct = rb["pred"] == rb["true"]
    if a_correct and b_correct:
        both_right += 1
    elif a_correct and not b_correct:
        a_right_b_wrong += 1
    elif not a_correct and b_correct:
        a_wrong_b_right += 1
    else:
        both_wrong += 1

table = [[both_right, a_right_b_wrong], [a_wrong_b_right, both_wrong]]
result = mcnemar(table, exact=False, correction=True)
print(f"\nMcNemar's test (paired, same {len(preds_a)} test images):")
print(f"  both correct: {both_right}, only A correct: {a_right_b_wrong}, only B correct: {a_wrong_b_right}, both wrong: {both_wrong}")
print(f"  statistic={result.statistic:.2f}, p-value={result.pvalue:.2e}")
print(f"  {'Significant at p<0.001' if result.pvalue < 0.001 else 'Not significant at p<0.001'}")
