"""
Benchmark harness: evaluates our TextEmotionModel (services/text_service/text_model.py,
including the negation-dampening fix) against the GoEmotions test split, using the
official Ekman mapping from the GoEmotions paper (google-research/google-research repo)
to reduce its 27 fine-grained + neutral labels down to our 7-class schema.

Only single-label examples are used (GoEmotions is natively multi-label; taking
single-label examples is the standard simplification for this kind of evaluation
and avoids ambiguous ground truth).

Usage:
    python3 eval_text_model.py --out results/text_model_goemotions.json [--limit N]
"""
import argparse
import json
import sys
import time
from pathlib import Path

from datasets import load_dataset
from sklearn.metrics import classification_report, confusion_matrix

sys.path.insert(0, str(Path(__file__).parent.parent / "services" / "text_service"))
from text_model import TextEmotionModel  # noqa: E402

UNIFIED_EMOTIONS = ["angry", "disgusted", "fearful", "happy", "neutral", "sad", "surprised"]

# Official Ekman mapping, from https://github.com/google-research/google-research/
# blob/master/goemotions/data/ekman_mapping.json — reduces GoEmotions' 27 fine-grained
# labels to Ekman's 6 basic emotions; "neutral" is already a native GoEmotions label.
EKMAN_MAPPING = {
    "anger": ["anger", "annoyance", "disapproval"],
    "disgust": ["disgust"],
    "fear": ["fear", "nervousness"],
    "joy": ["joy", "amusement", "approval", "excitement", "gratitude", "love",
            "optimism", "relief", "pride", "admiration", "desire", "caring"],
    "sadness": ["sadness", "disappointment", "embarrassment", "grief", "remorse"],
    "surprise": ["surprise", "realization", "confusion", "curiosity"],
}
EKMAN_TO_UNIFIED = {
    "anger": "angry", "disgust": "disgusted", "fear": "fearful",
    "joy": "happy", "sadness": "sad", "surprise": "surprised",
}


def build_fine_to_unified(label_names):
    fine_to_ekman = {}
    for ekman, fines in EKMAN_MAPPING.items():
        for fine in fines:
            fine_to_ekman[fine] = ekman
    fine_to_unified = {}
    for i, name in enumerate(label_names):
        if name == "neutral":
            fine_to_unified[i] = "neutral"
        elif name in fine_to_ekman:
            fine_to_unified[i] = EKMAN_TO_UNIFIED[fine_to_ekman[name]]
        else:
            fine_to_unified[i] = None  # shouldn't happen — every GoEmotions label maps
    return fine_to_unified


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    print("Loading GoEmotions test split...")
    ds = load_dataset("go_emotions", "simplified", split="test")
    label_names = ds.features["labels"].feature.names
    fine_to_unified = build_fine_to_unified(label_names)

    # Keep only single-label examples for unambiguous ground truth
    examples = [(ex["text"], ex["labels"][0]) for ex in ds if len(ex["labels"]) == 1]
    examples = [(t, fine_to_unified[l]) for t, l in examples if fine_to_unified[l] is not None]
    if args.limit:
        examples = examples[: args.limit]
    print(f"{len(examples)} single-label test examples after Ekman mapping.")

    print("Loading TextEmotionModel (with negation-dampening fix)...")
    model = TextEmotionModel()

    y_true, y_pred, raw = [], [], []
    start = time.time()
    for i, (text, true_label) in enumerate(examples):
        result = model.predict(text)
        pred_label = result["dominant_emotion"]
        y_true.append(true_label)
        y_pred.append(pred_label)
        raw.append({"idx": i, "text": text, "true": true_label, "pred": pred_label,
                     "confidence": round(result["confidence"], 4)})
        if (i + 1) % 200 == 0:
            elapsed = time.time() - start
            rate = (i + 1) / elapsed
            eta = (len(examples) - i - 1) / rate
            print(f"  {i+1}/{len(examples)} — {rate:.1f} ex/s — ETA {eta/60:.1f} min")

    report = classification_report(y_true, y_pred, labels=UNIFIED_EMOTIONS, output_dict=True, zero_division=0)
    cm = confusion_matrix(y_true, y_pred, labels=UNIFIED_EMOTIONS)

    result = {
        "model": "MoodScript TextEmotionModel (j-hartmann/emotion-english-distilroberta-base + negation dampening)",
        "eval_set": "GoEmotions test split, Ekman-mapped, single-label only",
        "n_examples": len(examples),
        "elapsed_seconds": round(time.time() - start, 1),
        "overall_accuracy": report["accuracy"],
        "per_class": {label: report[label] for label in UNIFIED_EMOTIONS},
        "confusion_matrix": {"labels": UNIFIED_EMOTIONS, "matrix": cm.tolist()},
        "raw_predictions": raw,
    }
    with open(args.out, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\nOverall accuracy: {report['accuracy']*100:.2f}%")
    print(f"{'CLASS':<12}{'PRECISION':<12}{'RECALL':<12}{'F1':<12}")
    for label in UNIFIED_EMOTIONS:
        r = report[label]
        print(f"{label:<12}{r['precision']*100:<12.1f}{r['recall']*100:<12.1f}{r['f1-score']*100:<12.1f}")
    print(f"\nSaved to {args.out}")


if __name__ == "__main__":
    main()
