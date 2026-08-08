"""Isolates which part of the deployed TEXT pipeline helps and which hurts.

The journal-domain benchmark showed something that needs explaining: the RAW
j-hartmann classifier scores 64.49% on those 1,056 texts while MoodScript's
deployed pipeline — the same base model wrapped in sentence segmentation,
position/length/confidence-weighted aggregation and syntax-aware negation
dampening — scores only 60.04%.

The wrapper is costing 4.45 points. This ablates it component by component on the
identical split to find out which part is responsible.

The negation rule is the prime suspect: it deliberately moves probability mass to
neutral, and the deployed pipeline predicts neutral 107 times against 57 for the
raw model. That rule was validated on 49 hand-written cases (72% -> 78%); this is
the first time it has been measured on a thousand-plus in-domain texts.
"""
import argparse
import json
import os
import sys

import numpy as np
from sklearn.metrics import f1_score
from statsmodels.stats.contingency_tables import mcnemar

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                                "services", "text_service"))

UNIFIED = ["angry", "disgusted", "fearful", "happy", "neutral", "sad", "surprised"]
_HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paired-set", default="paired_set_journal.json")
    args = ap.parse_args()

    import spacy
    from transformers import pipeline
    from text_model import JHARTMANN_TO_UNIFIED, TextEmotionModel

    data = json.load(open(os.path.join(_HERE, "results", args.paired_set)))
    tst = [p for p in data["pairs"] if p["split"] == "test"]
    texts = [p["text"] for p in tst]
    y = [p["true"] for p in tst]
    print(f"journal-domain test texts: {len(texts)}\n")

    nlp = spacy.load("en_core_web_sm")
    clf = pipeline("text-classification",
                   model="j-hartmann/emotion-english-distilroberta-base",
                   top_k=None, device=-1)
    tm = TextEmotionModel()          # for its _has_negation / _dampen / _weighted_aggregate

    def classify(sent):
        out = clf(sent[:512])
        if out and isinstance(out[0], list):
            out = out[0]
        d = {e: 0.0 for e in UNIFIED}
        for r in out:
            d[JHARTMANN_TO_UNIFIED.get(r["label"].lower(), "neutral")] += r["score"]
        return d

    variants = {"A whole text, no wrapper": [],
                "B sentence-split + weighted agg": [],
                "C  + negation dampening (DEPLOYED)": []}

    for i, t in enumerate(texts):
        if i and i % 250 == 0:
            print(f"  {i}/{len(texts)}", flush=True)

        # A: classify the entry as one unit
        d = classify(t)
        variants["A whole text, no wrapper"].append(max(d, key=d.get))

        # B / C: per-sentence, then MoodScript's own aggregation
        doc = nlp(t)
        sents = [s for s in doc.sents if s.text.strip()]
        res_plain, res_neg = [], []
        for s in sents:
            base = classify(s.text)
            res_plain.append((s.text, {"emotion": max(base, key=base.get),
                                       "confidence": max(base.values()),
                                       "all_scores": base}))
            if tm._has_negation(s):
                damp = tm._dampen_for_negation(dict(base))
            else:
                damp = base
            res_neg.append((s.text, {"emotion": max(damp, key=damp.get),
                                     "confidence": max(damp.values()),
                                     "all_scores": damp}))
        for key, res in (("B sentence-split + weighted agg", res_plain),
                         ("C  + negation dampening (DEPLOYED)", res_neg)):
            variants[key].append(tm._weighted_aggregate(res)["dominant_emotion"] if res else "neutral")

    print(f"\n{'VARIANT':<40}{'ACC %':>8}{'MACRO-F1':>10}{'NEUTRAL':>9}")
    print("-" * 67)
    preds = {}
    for name, p in variants.items():
        acc = float(np.mean([a == b for a, b in zip(p, y)]))
        f1 = float(f1_score(y, p, average="macro", zero_division=0))
        print(f"{name:<40}{acc*100:>8.2f}{f1*100:>10.2f}{sum(1 for x in p if x=='neutral'):>9}")
        preds[name] = p

    def compare(n1, n2):
        a = np.array([x == t for x, t in zip(preds[n1], y)])
        b = np.array([x == t for x, t in zip(preds[n2], y)])
        n10, n01 = int((a & ~b).sum()), int((~a & b).sum())
        r = mcnemar([[int((a & b).sum()), n10], [n01, int((~a & ~b).sum())]],
                    exact=False, correction=True)
        print(f"  {n1.strip()}  vs  {n2.strip()}")
        print(f"    former-only correct {n10}, latter-only {n01}, p={r.pvalue:.4g} "
              f"-> {'significant' if r.pvalue < 0.05 else 'not significant'}")

    print("\npaired comparisons:")
    compare("A whole text, no wrapper", "C  + negation dampening (DEPLOYED)")
    compare("B sentence-split + weighted agg", "C  + negation dampening (DEPLOYED)")
    compare("A whole text, no wrapper", "B sentence-split + weighted agg")

    out = os.path.join(_HERE, "results", "text_pipeline_ablation.json")
    with open(out, "w") as f:
        json.dump({"n": len(texts),
                   "variants": {k: float(np.mean([a == b for a, b in zip(v, y)]))
                                for k, v in variants.items()}}, f, indent=2)
    print(f"\nSaved -> {out}")


if __name__ == "__main__":
    main()
