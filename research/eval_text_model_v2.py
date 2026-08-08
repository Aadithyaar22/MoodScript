"""Verify the updated production text pipeline end-to-end on the journal split.

This runs the ACTUAL TextEmotionModel.predict() from services/text_service — not a
reimplementation — over the same 1,056 held-out journal texts the model-selection
benchmark used, so the number it prints is what production will really score.

Two changes are under test together:
  * the headline label comes from classifying the whole entry, not from the
    position/length/confidence-weighted average of per-sentence predictions
  * the syntax-triggered negation dampening is gone from the serving path

Expected: ~64.5% against the 60.04% the old pipeline scored on this split.

roberta-large would reach 67.33% here but peaks at 1.82GB resident against this
service's 2Gi Cloud Run cap, so the checkpoint is unchanged. Resident memory is
reported below to keep that constraint visible.
"""
import json
import os
import resource
import sys
import time

import numpy as np
from sklearn.metrics import f1_score
from statsmodels.stats.contingency_tables import mcnemar

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "services", "text_service"))

UNIFIED = ["angry", "disgusted", "fearful", "happy", "neutral", "sad", "surprised"]


def rss_gb():
    # ru_maxrss is bytes on macOS, kilobytes on Linux
    v = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return v / (1024 ** 3) if sys.platform == "darwin" else v / (1024 ** 2)


def main():
    os.environ.setdefault("ENABLE_CLINICAL_TONE", "false")  # matches Cloud Run env

    data = json.load(open(os.path.join(_HERE, "results", "paired_set_journal.json")))
    tst = [p for p in data["pairs"] if p["split"] == "test"]
    texts = [p["text"] for p in tst]
    y = [p["true"] for p in tst]
    old = [p["text_pred"] for p in tst]  # cached predictions of the old pipeline
    print(f"journal-domain test texts: {len(texts)}", flush=True)

    print(f"RSS before load: {rss_gb():.2f} GB", flush=True)
    from text_model import EMOTION_MODEL, USE_SENTENCE_AGGREGATE, TextEmotionModel
    print(f"model={EMOTION_MODEL}  sentence_aggregate={USE_SENTENCE_AGGREGATE}", flush=True)
    tm = TextEmotionModel()
    print(f"RSS after load:  {rss_gb():.2f} GB   (Cloud Run limit 2Gi)", flush=True)

    new, t0 = [], time.time()
    for i, t in enumerate(texts):
        if i and i % 100 == 0:
            el = time.time() - t0
            print(f"  {i}/{len(texts)}  {el/i*1000:.0f} ms/entry  "
                  f"eta {(len(texts)-i)*el/i/60:.1f} min", flush=True)
        try:
            new.append(tm.predict(t)["dominant_emotion"])
        except Exception as e:
            print(f"  predict failed on #{i}: {type(e).__name__}: {e}", flush=True)
            new.append("neutral")
    ms = (time.time() - t0) / len(texts) * 1000
    print(f"\n{ms:.0f} ms/entry end-to-end (whole-text + per-sentence arc + spaCy)\n", flush=True)

    print(f"{'PIPELINE':<34}{'ACC %':>8}{'MACRO-F1':>10}{'NEUTRAL':>9}")
    print("-" * 61)
    for name, p in (("old (deployed until now)", old), ("new (this change)", new)):
        print(f"{name:<34}{np.mean([a == b for a, b in zip(p, y)])*100:>8.2f}"
              f"{f1_score(y, p, average='macro', zero_division=0)*100:>10.2f}"
              f"{sum(1 for x in p if x == 'neutral'):>9}")

    a = np.array([x == t for x, t in zip(new, y)])
    b = np.array([x == t for x, t in zip(old, y)])
    n10, n01 = int((a & ~b).sum()), int((~a & b).sum())
    r = mcnemar([[int((a & b).sum()), n10], [n01, int((~a & ~b).sum())]],
                exact=False, correction=True)
    print(f"\nMcNemar: new-only correct {n10}, old-only correct {n01}, p={r.pvalue:.4g}"
          f" -> {'significant' if r.pvalue < 0.05 else 'NOT significant'}")

    # coarser groupings, for the product question of how often the VALENCE is right
    groups = {"positive": {"happy", "surprised"},
              "negative": {"angry", "disgusted", "fearful", "sad"},
              "neutral": {"neutral"}}
    def g(lbl):
        return next((k for k, v in groups.items() if lbl in v), lbl)
    print(f"3-class valence accuracy (same predictions, scored coarsely): "
          f"{np.mean([g(p) == g(t) for p, t in zip(new, y)])*100:.2f}%")

    out = os.path.join(_HERE, "results", "text_model_v2.json")
    with open(out, "w") as f:
        json.dump({"n": len(texts), "model": EMOTION_MODEL, "ms_per_entry": ms,
                   "rss_gb": rss_gb(),
                   "old_acc": float(np.mean([x == t for x, t in zip(old, y)])),
                   "new_acc": float(np.mean([x == t for x, t in zip(new, y)])),
                   "mcnemar_p": float(r.pvalue), "preds": new}, f, indent=2)
    print(f"\nSaved -> {out}")


if __name__ == "__main__":
    main()
