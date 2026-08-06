"""
Benchmark harness: evaluates candidate text-emotion models against the same GoEmotions
test-split methodology used for the current model (research/eval_text_model.py,
research/results/text_model_goemotions.json = 43.75% baseline), for a direct,
apples-to-apples comparison — same rigor as the face-model FER2013 benchmark.

Candidates:
  - j-hartmann/emotion-english-roberta-large  (same schema as current model, larger backbone)
  - SamLowe/roberta-base-go_emotions          (native GoEmotions model — in-domain for this
                                                eval set, so a win here is expected and less
                                                informative about general/journal-style text;
                                                still worth measuring, with that caveat noted)

Usage:
    python3 eval_text_candidates.py --model j-hartmann/emotion-english-roberta-large --kind ekman7 --out results/candidate_roberta_large.json
    python3 eval_text_candidates.py --model SamLowe/roberta-base-go_emotions --kind goemotions28 --out results/candidate_samlowe.json
"""
import argparse
import json
import time

from datasets import load_dataset
from transformers import pipeline
from sklearn.metrics import classification_report, confusion_matrix

UNIFIED_EMOTIONS = ["angry", "disgusted", "fearful", "happy", "neutral", "sad", "surprised"]

EKMAN_MAPPING = {
    "anger": ["anger", "annoyance", "disapproval"],
    "disgust": ["disgust"],
    "fear": ["fear", "nervousness"],
    "joy": ["joy", "amusement", "approval", "excitement", "gratitude", "love",
            "optimism", "relief", "pride", "admiration", "desire", "caring"],
    "sadness": ["sadness", "disappointment", "embarrassment", "grief", "remorse"],
    "surprise": ["surprise", "realization", "confusion", "curiosity"],
}
EKMAN_TO_UNIFIED = {"anger": "angry", "disgust": "disgusted", "fear": "fearful",
                     "joy": "happy", "sadness": "sad", "surprise": "surprised"}
FINE_TO_UNIFIED = {"neutral": "neutral"}
for ekman, fines in EKMAN_MAPPING.items():
    for fine in fines:
        FINE_TO_UNIFIED[fine] = EKMAN_TO_UNIFIED[ekman]

# Same 7-class schema as our current model — a direct label rename, no Ekman step needed.
EKMAN7_TO_UNIFIED = {"anger": "angry", "disgust": "disgusted", "fear": "fearful",
                      "joy": "happy", "neutral": "neutral", "sadness": "sad", "surprise": "surprised"}


def build_fine_to_unified(label_names):
    m = {}
    for i, name in enumerate(label_names):
        m[i] = FINE_TO_UNIFIED.get(name)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--kind", required=True, choices=["ekman7", "goemotions28"],
                     help="ekman7: model already outputs our 7-class schema directly. "
                          "goemotions28: model outputs GoEmotions' 28 fine labels, map via Ekman.")
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    print("Loading GoEmotions test split...")
    ds = load_dataset("go_emotions", "simplified", split="test")
    label_names = ds.features["labels"].feature.names
    fine_to_unified = build_fine_to_unified(label_names)

    examples = [(ex["text"], ex["labels"][0]) for ex in ds if len(ex["labels"]) == 1]
    examples = [(t, fine_to_unified[l]) for t, l in examples if fine_to_unified[l] is not None]
    if args.limit:
        examples = examples[: args.limit]
    print(f"{len(examples)} single-label test examples after Ekman mapping.")

    print(f"Loading model: {args.model}")
    clf = pipeline("text-classification", model=args.model, top_k=None, device=-1)

    y_true, y_pred, raw = [], [], []
    start = time.time()
    for i, (text, true_label) in enumerate(examples):
        preds = clf(text[:512])
        if preds and isinstance(preds[0], list):
            preds = preds[0]
        top = max(preds, key=lambda p: p["score"])
        raw_label = top["label"].lower()

        if args.kind == "ekman7":
            pred_label = EKMAN7_TO_UNIFIED.get(raw_label, raw_label)
        else:  # goemotions28
            pred_label = FINE_TO_UNIFIED.get(raw_label, "neutral")

        y_true.append(true_label)
        y_pred.append(pred_label)
        raw.append({"idx": i, "text": text, "true": true_label, "pred": pred_label,
                     "confidence": round(top["score"], 4)})
        if (i + 1) % 500 == 0:
            elapsed = time.time() - start
            rate = (i + 1) / elapsed
            eta = (len(examples) - i - 1) / rate
            print(f"  {i+1}/{len(examples)} — {rate:.1f} ex/s — ETA {eta/60:.1f} min")

    report = classification_report(y_true, y_pred, labels=UNIFIED_EMOTIONS, output_dict=True, zero_division=0)
    cm = confusion_matrix(y_true, y_pred, labels=UNIFIED_EMOTIONS)

    result = {
        "model": args.model,
        "eval_set": "GoEmotions test split, Ekman-mapped, single-label only (same as baseline)",
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
