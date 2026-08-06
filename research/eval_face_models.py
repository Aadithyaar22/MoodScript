"""
Benchmark harness: evaluates candidate face-emotion models against the standard
FER2013 test split (7,178 images — the public+private test sets from the original
Kaggle competition, loaded via the clip-benchmark/wds_fer2013 mirror on Hugging Face).

Produces, per model: per-class precision/recall/F1, a confusion matrix, overall
accuracy, and raw predictions (for a paired McNemar's test between models, run
separately by compare_models.py once both prediction files exist).

Usage:
    python3 eval_face_models.py --model trpakov/vit-face-expression --out results/trpakov.json
    python3 eval_face_models.py --model dima806/facial_emotions_image_detection --out results/dima806.json
"""
import argparse
import json
import time

from datasets import load_dataset
from transformers import pipeline
from sklearn.metrics import classification_report, confusion_matrix

# FER2013 label order (0-6) for the clip-benchmark/wds_fer2013 mirror's `cls` field.
# NOTE: this differs from the classic Kaggle CSV order (...,4=Sad,5=Surprise,6=Neutral)
# — this mirror stores classes 4-6 as Neutral,Sad,Surprise instead. Verified empirically
# by cross-checking per-class ground-truth counts against FER2013's well-documented
# official test-set distribution (Angry 958, Disgust 111, Fear 1024, Happy 1774,
# Sad 1247, Surprise 831, Neutral 1233) until the row sums lined up — the naive
# classic-Kaggle-order assumption silently scrambled the last 3 classes and dropped
# reported accuracy from ~71% to ~42% before this was caught.
FER2013_LABELS = ["angry", "disgusted", "fearful", "happy", "neutral", "sad", "surprised"]

# Maps each candidate model's own output label strings to our canonical set above.
LABEL_MAPS = {
    "trpakov/vit-face-expression": {
        "angry": "angry", "disgust": "disgusted", "fear": "fearful",
        "happy": "happy", "sad": "sad", "surprise": "surprised", "neutral": "neutral",
    },
    "dima806/facial_emotions_image_detection": {
        "angry": "angry", "disgust": "disgusted", "fear": "fearful",
        "happy": "happy", "sad": "sad", "surprise": "surprised", "neutral": "neutral",
    },
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=None, help="Subsample for a quick smoke test")
    args = ap.parse_args()

    if args.model not in LABEL_MAPS:
        raise SystemExit(f"No label map defined for {args.model} — add one to LABEL_MAPS first.")
    label_map = LABEL_MAPS[args.model]

    print(f"Loading FER2013 test split...")
    ds = load_dataset("clip-benchmark/wds_fer2013", split="test")
    if args.limit:
        ds = ds.select(range(args.limit))
    print(f"{len(ds)} test images loaded.")

    print(f"Loading model: {args.model}")
    clf = pipeline("image-classification", model=args.model, top_k=None, device=-1)

    y_true, y_pred, raw = [], [], []
    start = time.time()
    for i, ex in enumerate(ds):
        image = ex["jpg"].convert("RGB")
        true_label = FER2013_LABELS[ex["cls"]]
        preds = clf(image)
        top = max(preds, key=lambda p: p["score"])
        pred_label = label_map.get(top["label"].lower(), top["label"].lower())

        y_true.append(true_label)
        y_pred.append(pred_label)
        raw.append({"idx": i, "true": true_label, "pred": pred_label, "confidence": round(top["score"], 4)})

        if (i + 1) % 500 == 0:
            elapsed = time.time() - start
            rate = (i + 1) / elapsed
            eta = (len(ds) - i - 1) / rate
            print(f"  {i+1}/{len(ds)} — {rate:.1f} img/s — ETA {eta/60:.1f} min")

    report = classification_report(y_true, y_pred, labels=FER2013_LABELS, output_dict=True, zero_division=0)
    cm = confusion_matrix(y_true, y_pred, labels=FER2013_LABELS)

    result = {
        "model": args.model,
        "n_images": len(ds),
        "elapsed_seconds": round(time.time() - start, 1),
        "overall_accuracy": report["accuracy"],
        "per_class": {label: report[label] for label in FER2013_LABELS},
        "confusion_matrix": {
            "labels": FER2013_LABELS,
            "matrix": cm.tolist(),
        },
        "raw_predictions": raw,
    }

    with open(args.out, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\nOverall accuracy: {report['accuracy']*100:.2f}%")
    print(f"{'CLASS':<12}{'PRECISION':<12}{'RECALL':<12}{'F1':<12}")
    for label in FER2013_LABELS:
        r = report[label]
        print(f"{label:<12}{r['precision']*100:<12.1f}{r['recall']*100:<12.1f}{r['f1-score']*100:<12.1f}")
    print(f"\nSaved to {args.out}")


if __name__ == "__main__":
    main()
