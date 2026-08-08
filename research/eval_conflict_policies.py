"""Compares every conflict-resolution policy on the cases where they actually apply.

The LLM arbitration layer exists to handle one situation: both modalities disagree at
comparable confidence, so numeric fusion reports `conflict_resolved_to_*`. This script
isolates exactly that subset of the test split and asks which policy resolves it best.

Run for both paired sets to check the finding is not an artefact of one text domain:

    python research/eval_conflict_policies.py --paired-set paired_set.json
    python research/eval_conflict_policies.py --paired-set paired_set_journal.json

Arbitration accuracy is read from the corresponding eval_arbiter_paired.py output so
this script needs no LLM calls.
"""
import argparse
import json
import os
import sys

import numpy as np
from scipy.optimize import minimize_scalar

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from models.fusion import FusionLayer  # noqa: E402

UNIFIED = ["angry", "disgusted", "fearful", "happy", "neutral", "sad", "surprised"]
IDX = {e: i for i, e in enumerate(UNIFIED)}
_HERE = os.path.dirname(os.path.abspath(__file__))


def vec(d):
    v = np.array([d[e] for e in UNIFIED], float)
    s = v.sum()
    return v / s if s > 0 else np.full(7, 1 / 7)


def ts(P, T):
    l = np.log(np.clip(P, 1e-12, 1)) / T
    l -= l.max(1, keepdims=True)
    e = np.exp(l)
    return e / e.sum(1, keepdims=True)


def fitT(P, y):
    def nll(T):
        if T <= 0:
            return 1e9
        return float(-np.mean(np.log(np.clip(ts(P, T)[np.arange(len(y)), y], 1e-12, 1))))
    return float(minimize_scalar(nll, bounds=(0.05, 20), method="bounded").x)


def fuse(A, B):
    wt, wf = 0.55 * A.max(1, keepdims=True), 0.45 * B.max(1, keepdims=True)
    t = wt + wf
    t[t == 0] = 1
    return (wt / t) * A + (wf / t) * B


def class_reliability(P, y, K=7, smoothing=5.0):
    pred = P.argmax(1)
    overall = float((pred == y).mean())
    r = np.zeros(K)
    for c in range(K):
        m = pred == c
        n = int(m.sum())
        hits = float((y[m] == c).sum()) if n else 0.0
        r[c] = (hits + smoothing * overall) / (n + smoothing)
    return r


def fuse_v2(A, B, rel_t, rel_f):
    """Class-conditional reliability weighting + log-linear pooling (fusion v2)."""
    at = (rel_t[A.argmax(1)] * A.max(1))[:, None] * 0.55
    af = (rel_f[B.argmax(1)] * B.max(1))[:, None] * 0.45
    tot = at + af
    tot[tot == 0] = 1.0
    at, af = at / tot, af / tot
    logp = at * np.log(np.clip(A, 1e-12, 1)) + af * np.log(np.clip(B, 1e-12, 1))
    logp -= logp.max(1, keepdims=True)
    e = np.exp(logp)
    return e / e.sum(1, keepdims=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paired-set", default="paired_set.json")
    ap.add_argument("--arbiter-result", default=None,
                    help="eval_arbiter_paired.py output for the same set (optional)")
    args = ap.parse_args()

    data = json.load(open(os.path.join(_HERE, "results", args.paired_set)))
    print(f"paired set: {args.paired_set}")
    print(f"text source: {data.get('text_source','?')}")

    cal = [p for p in data["pairs"] if p["split"] == "calib"]
    tst = [p for p in data["pairs"] if p["split"] == "test"]
    Tc = np.stack([vec(p["text_dist"]) for p in cal])
    Fc = np.stack([vec(p["face_dist"]) for p in cal])
    yc = np.array([IDX[p["true"]] for p in cal])
    T_text, T_face = fitT(Tc, yc), fitT(Fc, yc)

    fusion = FusionLayer()
    sub = []
    for p in tst:
        tr = {"dominant_emotion": p["text_pred"], "confidence": max(p["text_dist"].values()),
              "all_scores": p["text_dist"]}
        fr = {"emotion": p["face_pred"], "confidence": max(p["face_dist"].values()),
              "all_scores": p["face_dist"]}
        if fusion.fuse(tr, fr).get("resolution_reason", "").startswith("conflict_resolved_to_"):
            sub.append(p)

    T = np.stack([vec(p["text_dist"]) for p in sub])
    F = np.stack([vec(p["face_dist"]) for p in sub])
    y = np.array([IDX[p["true"]] for p in sub])

    rel_t = class_reliability(ts(Tc, T_text), yc)
    rel_f = class_reliability(ts(Fc, T_face), yc)
    rows = [
        ("text only", float((T.argmax(1) == y).mean())),
        ("face only", float((F.argmax(1) == y).mean())),
        ("numeric fusion (deployed)", float((fuse(T, F).argmax(1) == y).mean())),
        ("calibrated linear fusion",
         float((fuse(ts(T, T_text), ts(F, T_face)).argmax(1) == y).mean())),
        ("log-linear + class reliability (v2)",
         float((fuse_v2(ts(T, T_text), ts(F, T_face), rel_t, rel_f).argmax(1) == y).mean())),
    ]

    arb_file = args.arbiter_result or (
        "arbiter_paired_journal.json" if "journal" in args.paired_set else "arbiter_paired.json")
    arb_path = os.path.join(_HERE, "results", arb_file)
    if os.path.exists(arb_path):
        a = json.load(open(arb_path))
        acc = a["accuracy"].get("LLM arbitration (proposed)")
        if acc is not None:
            rows.insert(3, ("LLM arbitration (deployed extra call)", float(acc)))

    print(f"\nCONFLICT CASES ONLY — n={len(sub)} of {len(tst)} test pairs "
          f"({len(sub)/len(tst)*100:.1f}%)")
    print(f"{'policy':<40}{'acc %':>8}")
    print("-" * 48)
    for name, a in rows:
        print(f"{name:<40}{a*100:>8.2f}")

    best = max(rows, key=lambda r: r[1])
    print(f"\nbest policy: {best[0]} ({best[1]*100:.2f}%)")

    out = os.path.join(_HERE, "results",
                       f"conflict_policies_{'journal' if 'journal' in args.paired_set else 'goemotions'}.json")
    with open(out, "w") as f:
        json.dump({"paired_set": args.paired_set,
                   "text_source": data.get("text_source"),
                   "n_conflict": len(sub), "n_test": len(tst),
                   "temperature": {"text": T_text, "face": T_face},
                   "policies": {n: a for n, a in rows}}, f, indent=2)
    print(f"Saved -> {out}")


if __name__ == "__main__":
    main()
