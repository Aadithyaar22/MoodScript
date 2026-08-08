"""Benchmark candidate text-emotion models on journal-domain text.

The deployed text model is the weakest component of the system and the primary one:
a face photo is optional, so on text-only entries it decides alone. This evaluates
replacements on the 1,056 held-out journal-style texts from the paired benchmark —
first-person narrative, which is what the product actually receives, rather than the
Reddit comments of GoEmotions.

Every candidate is scored on the identical split, so McNemar's paired test applies.

Note on the 'neutral' class: this benchmark has no neutral examples (EmpatheticDialogues
has no neutral category), so a model that hedges toward neutral is penalised here more
than it would be in production, where neutral is common. Per-class numbers below make
that visible rather than hiding it in the headline.
"""
import argparse
import json
import os
import time

import numpy as np
from sklearn.metrics import f1_score
from statsmodels.stats.contingency_tables import mcnemar

UNIFIED = ["angry", "disgusted", "fearful", "happy", "neutral", "sad", "surprised"]
_HERE = os.path.dirname(os.path.abspath(__file__))

# label -> unified, per candidate model's own label vocabulary
EKMAN7 = {"anger": "angry", "disgust": "disgusted", "fear": "fearful", "joy": "happy",
          "neutral": "neutral", "sadness": "sad", "surprise": "surprised"}
GOEMOTIONS = {
    "anger": "angry", "annoyance": "angry", "disapproval": "angry",
    "disgust": "disgusted",
    "fear": "fearful", "nervousness": "fearful",
    "joy": "happy", "amusement": "happy", "approval": "happy", "excitement": "happy",
    "gratitude": "happy", "love": "happy", "optimism": "happy", "relief": "happy",
    "pride": "happy", "admiration": "happy", "desire": "happy", "caring": "happy",
    "sadness": "sad", "disappointment": "sad", "embarrassment": "sad", "grief": "sad",
    "remorse": "sad",
    "surprise": "surprised", "realization": "surprised", "confusion": "surprised",
    "curiosity": "surprised",
    "neutral": "neutral",
}

CANDIDATES = [
    ("j-hartmann/emotion-english-distilroberta-base", EKMAN7, "DEPLOYED (raw, no negation fix)"),
    ("j-hartmann/emotion-english-roberta-large", EKMAN7, "larger sibling"),
    ("SamLowe/roberta-base-go_emotions", GOEMOTIONS, "GoEmotions specialist"),
    ("cirimus/modernbert-base-go-emotions", GOEMOTIONS, "ModernBERT architecture"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paired-set", default="paired_set_journal.json")
    args = ap.parse_args()

    from transformers import pipeline

    data = json.load(open(os.path.join(_HERE, "results", args.paired_set)))
    tst = [p for p in data["pairs"] if p["split"] == "test"]
    texts = [p["text"] for p in tst]
    y = [p["true"] for p in tst]
    print(f"journal-domain test texts: {len(texts)}")
    print(f"source: {data.get('text_source','?')}\n")

    results = {}
    # the deployed pipeline's own predictions, already cached (includes negation fix)
    results["MoodScript deployed pipeline"] = [p["text_pred"] for p in tst]

    for model_id, mapping, note in CANDIDATES:
        print(f"loading {model_id} ({note})...", flush=True)
        try:
            clf = pipeline("text-classification", model=model_id, top_k=None, device=-1)
        except Exception as e:
            print(f"  SKIP: {type(e).__name__}: {str(e)[:110]}\n")
            continue
        preds, t0 = [], time.time()
        for i, t in enumerate(texts):
            if i and i % 250 == 0:
                print(f"    {i}/{len(texts)}", flush=True)
            try:
                out = clf(t[:512])
                if out and isinstance(out[0], list):
                    out = out[0]
                agg = {}
                for r in out:
                    u = mapping.get(r["label"].lower())
                    if u:
                        agg[u] = agg.get(u, 0.0) + r["score"]
                preds.append(max(agg, key=agg.get) if agg else "neutral")
            except Exception:
                preds.append("neutral")
        results[model_id] = preds
        print(f"  done in {time.time()-t0:.0f}s\n", flush=True)

    print(f"{'MODEL':<48}{'ACC %':>8}{'MACRO-F1':>10}{'NEUTRAL PREDS':>15}")
    print("-" * 81)
    base = None
    rows = []
    for name, preds in results.items():
        acc = float(np.mean([a == b for a, b in zip(preds, y)]))
        f1 = float(f1_score(y, preds, average="macro", zero_division=0))
        nneu = sum(1 for p in preds if p == "neutral")
        rows.append({"model": name, "accuracy": acc, "macro_f1": f1, "neutral_preds": nneu})
        print(f"{name[:47]:<48}{acc*100:>8.2f}{f1*100:>10.2f}{nneu:>15}")
        if base is None:
            base = preds

    print(f"\n(the benchmark contains 0 neutral examples, so every neutral prediction "
          f"is an error here)")

    print("\nMcNemar vs the deployed pipeline:")
    for name, preds in results.items():
        if preds is base:
            continue
        a = np.array([p == t for p, t in zip(preds, y)])
        b = np.array([p == t for p, t in zip(base, y)])
        n10, n01 = int((a & ~b).sum()), int((~a & b).sum())
        r = mcnemar([[int((a & b).sum()), n10], [n01, int((~a & ~b).sum())]],
                    exact=False, correction=True)
        verdict = ("BETTER" if n10 > n01 else "WORSE") if r.pvalue < 0.05 else "no sig. difference"
        print(f"  {name[:44]:<46} p={r.pvalue:<10.4g} {verdict}")

    out = os.path.join(_HERE, "results", "text_journal_bench.json")
    with open(out, "w") as f:
        json.dump({"n": len(texts), "source": data.get("text_source"), "rows": rows}, f, indent=2)
    print(f"\nSaved -> {out}")


if __name__ == "__main__":
    main()
