"""One-off: recompute metrics from an already-run eval_face_models.py output whose
ground-truth labels used the wrong FER2013_LABELS order. Predictions are untouched
(the model itself was never wrong) — only the true-label remapping is corrected.
"""
import argparse
import json

from sklearn.metrics import classification_report, confusion_matrix

UNIFIED_EMOTIONS = ["angry", "disgusted", "fearful", "happy", "neutral", "sad", "surprised"]
# old (wrong) label -> correct label, for the specific bug described in eval_face_models.py
FIX_MAP = {"sad": "neutral", "surprised": "sad", "neutral": "surprised"}

ap = argparse.ArgumentParser()
ap.add_argument("--file", required=True)
args = ap.parse_args()

d = json.load(open(args.file))
y_true = [FIX_MAP.get(r["true"], r["true"]) for r in d["raw_predictions"]]
y_pred = [r["pred"] for r in d["raw_predictions"]]

report = classification_report(y_true, y_pred, labels=UNIFIED_EMOTIONS, output_dict=True, zero_division=0)
cm = confusion_matrix(y_true, y_pred, labels=UNIFIED_EMOTIONS)

d["overall_accuracy"] = report["accuracy"]
d["per_class"] = {label: report[label] for label in UNIFIED_EMOTIONS}
d["confusion_matrix"] = {"labels": UNIFIED_EMOTIONS, "matrix": cm.tolist()}
for r in d["raw_predictions"]:
    r["true"] = FIX_MAP.get(r["true"], r["true"])

with open(args.file, "w") as f:
    json.dump(d, f, indent=2)

print(f"Corrected accuracy: {report['accuracy']*100:.2f}%")
print(f"{'CLASS':<12}{'PRECISION':<12}{'RECALL':<12}{'F1':<12}")
for label in UNIFIED_EMOTIONS:
    r = report[label]
    print(f"{label:<12}{r['precision']*100:<12.1f}{r['recall']*100:<12.1f}{r['f1-score']*100:<12.1f}")
