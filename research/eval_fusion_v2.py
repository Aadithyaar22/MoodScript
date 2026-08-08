"""Stronger fusion: class-conditional reliability weighting with log-linear pooling.

MOTIVATION
----------
The deployed rule is LINEAR pooling with a scalar weight:

    P(e) = w_t·P_text(e) + w_f·P_face(e),   w_m ∝ prior_m · max(P_m)

Two structural weaknesses, both visible in the measurements:

1. Linear pooling cannot veto. If one modality assigns ~0 probability to a class,
   the other can still carry it, because the sum is dominated by the larger term.
   Log-linear pooling (a product of experts) multiplies instead of adds, so a
   confident "not this class" actually suppresses that class. Under conditional
   independence of the two modalities given the label, the product is the Bayesian
   combination; the linear sum is not.

2. A single scalar weight per modality assumes a modality is uniformly reliable
   across classes. It is not: on the calibration split the text model's precision
   varies enormously by class, so its vote deserves different trust depending on
   WHICH class it is voting for.

METHOD (fusion v2)
------------------
    a) temperature-calibrate each modality                     (fitted on calib split)
    b) estimate a class-conditional reliability r_m(c)         (calib split)
       = precision of modality m on the class it is predicting
    c) per-sample weight  a_m = r_m(argmax P_m) · max(P_m)     -> normalised
    d) combine by log-linear pooling:
           log P(e) ∝ a_t·log P_text(e) + a_f·log P_face(e)

Everything estimated on the calibration split only; all numbers below are on the
held-out test split.

Baselines reported alongside:
  - each modality alone
  - the deployed linear confidence-weighted rule
  - calibrated linear (the previous proposal)
  - multinomial logistic regression on the concatenated calibrated distributions,
    as a LEARNED reference for how much of the oracle ceiling is capturable
  - the oracle ceiling itself (either modality correct)
"""
import argparse
import json
import os

import numpy as np
from scipy.optimize import minimize_scalar
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from statsmodels.stats.contingency_tables import mcnemar

UNIFIED = ["angry", "disgusted", "fearful", "happy", "neutral", "sad", "surprised"]
IDX = {e: i for i, e in enumerate(UNIFIED)}
K = len(UNIFIED)
TEXT_PRIOR, FACE_PRIOR = 0.55, 0.45
_HERE = os.path.dirname(os.path.abspath(__file__))
EPS = 1e-12


def vec(d):
    v = np.array([d[e] for e in UNIFIED], float)
    s = v.sum()
    return v / s if s > 0 else np.full(K, 1 / K)


def ts(P, T):
    l = np.log(np.clip(P, EPS, 1)) / T
    l -= l.max(1, keepdims=True)
    e = np.exp(l)
    return e / e.sum(1, keepdims=True)


def fitT(P, y):
    def nll(T):
        if T <= 0:
            return 1e9
        return float(-np.mean(np.log(np.clip(ts(P, T)[np.arange(len(y)), y], EPS, 1))))
    return float(minimize_scalar(nll, bounds=(0.05, 20), method="bounded").x)


def ece(P, y, nb=10):
    c, a = P.max(1), (P.argmax(1) == y).astype(float)
    b = np.linspace(0, 1, nb + 1)
    o = 0.0
    for lo, hi in zip(b[:-1], b[1:]):
        m = (c > lo) & (c <= hi)
        if m.sum():
            o += m.sum() / len(c) * abs(c[m].mean() - a[m].mean())
    return float(o)


def class_reliability(P, y, smoothing=5.0):
    """Precision of this modality per predicted class, on the calibration split.
    Laplace-smoothed toward the modality's overall accuracy so rare classes with a
    handful of predictions do not produce a reliability of 0.0 or 1.0."""
    pred = P.argmax(1)
    overall = float((pred == y).mean())
    r = np.zeros(K)
    for c in range(K):
        m = pred == c
        n = int(m.sum())
        hits = float((y[m] == c).sum()) if n else 0.0
        r[c] = (hits + smoothing * overall) / (n + smoothing)
    return r


def fuse_linear(A, B, weighted=True):
    if weighted:
        wt, wf = TEXT_PRIOR * A.max(1, keepdims=True), FACE_PRIOR * B.max(1, keepdims=True)
        t = wt + wf
        t[t == 0] = 1
        wt, wf = wt / t, wf / t
    else:
        wt, wf = TEXT_PRIOR, FACE_PRIOR
    return wt * A + wf * B


def fuse_loglinear(A, B, rel_t, rel_f):
    """Class-conditional reliability weighting + log-linear (product) pooling."""
    at = (rel_t[A.argmax(1)] * A.max(1))[:, None] * TEXT_PRIOR
    af = (rel_f[B.argmax(1)] * B.max(1))[:, None] * FACE_PRIOR
    tot = at + af
    tot[tot == 0] = 1.0
    at, af = at / tot, af / tot
    logp = at * np.log(np.clip(A, EPS, 1)) + af * np.log(np.clip(B, EPS, 1))
    logp -= logp.max(1, keepdims=True)
    e = np.exp(logp)
    return e / e.sum(1, keepdims=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paired-set", default="paired_set.json")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    data = json.load(open(os.path.join(_HERE, "results", args.paired_set)))
    print(f"paired set: {args.paired_set}")
    print(f"text source: {data.get('text_source','?')}")

    def pack(s):
        sub = [p for p in data["pairs"] if p["split"] == s]
        return (np.stack([vec(p["text_dist"]) for p in sub]),
                np.stack([vec(p["face_dist"]) for p in sub]),
                np.array([IDX[p["true"]] for p in sub]))

    Tc, Fc, yc = pack("calib")
    Tt, Ft, yt = pack("test")

    T_text, T_face = fitT(Tc, yc), fitT(Fc, yc)
    Tc_c, Fc_c = ts(Tc, T_text), ts(Fc, T_face)
    Tt_c, Ft_c = ts(Tt, T_text), ts(Ft, T_face)

    rel_t = class_reliability(Tc_c, yc)
    rel_f = class_reliability(Fc_c, yc)
    print(f"\nclass-conditional reliability (calibration split)")
    print(f"{'class':<12}{'text':>8}{'face':>8}")
    for c, e in enumerate(UNIFIED):
        print(f"{e:<12}{rel_t[c]:>8.3f}{rel_f[c]:>8.3f}")

    rows = []

    def rep(name, P):
        pred = P.argmax(1)
        acc = float((pred == yt).mean())
        f1 = float(f1_score(yt, pred, average="macro", zero_division=0))
        rows.append({"strategy": name, "accuracy": acc, "macro_f1": f1, "ece": ece(P, yt)})
        print(f"{name:<44}{acc*100:>8.2f}{f1*100:>10.2f}{ece(P,yt):>9.4f}")
        return pred

    print(f"\n{'STRATEGY':<44}{'ACC %':>8}{'MACRO-F1':>10}{'ECE':>9}")
    print("-" * 71)
    rep("text only", Tt)
    pred_face = rep("face only", Ft)
    rep("linear, fixed weights (naive)", fuse_linear(Tt, Ft, False))
    pred_dep = rep("linear + confidence (deployed)", fuse_linear(Tt, Ft, True))
    pred_lin = rep("linear + confidence + calibration", fuse_linear(Tt_c, Ft_c, True))
    pred_v2 = rep("LOG-LINEAR + class reliability (v2)", fuse_loglinear(Tt_c, Ft_c, rel_t, rel_f))

    # learned reference: how much of the ceiling is capturable at all?
    lr = LogisticRegression(max_iter=2000, C=1.0)
    lr.fit(np.hstack([Tc_c, Fc_c]), yc)
    rep("learned logistic regression (reference)", lr.predict_proba(np.hstack([Tt_c, Ft_c])))

    oracle = float(((Tt.argmax(1) == yt) | (Ft.argmax(1) == yt)).mean())
    print(f"{'ORACLE ceiling (either correct)':<44}{oracle*100:>8.2f}")

    def paired(name, a_pred, b_pred, la, lb):
        a, b = a_pred == yt, b_pred == yt
        n10, n01 = int((a & ~b).sum()), int((~a & b).sum())
        r = mcnemar([[int((a & b).sum()), n10], [n01, int((~a & ~b).sum())]],
                    exact=False, correction=True)
        print(f"\nMcNemar — {name} (n={len(yt)})")
        print(f"  {la} only correct = {n10}   {lb} only correct = {n01}")
        print(f"  chi2={r.statistic:.3f}  p={r.pvalue:.4g}  -> "
              f"{'SIGNIFICANT' if r.pvalue < 0.05 else 'NOT significant'}")
        return {"n_a_only": n10, "n_b_only": n01, "chi2": float(r.statistic),
                "p_value": float(r.pvalue), "significant": bool(r.pvalue < 0.05)}

    sig = {
        "v2_vs_deployed": paired("v2 vs deployed", pred_v2, pred_dep, "v2", "deployed"),
        "v2_vs_calibrated_linear": paired("v2 vs calibrated-linear", pred_v2, pred_lin, "v2", "cal-linear"),
        "v2_vs_face_only": paired("v2 vs FACE-ONLY (the real test)", pred_v2, pred_face, "v2", "face"),
    }

    face_acc = float((pred_face == yt).mean())
    v2_acc = float((pred_v2 == yt).mean())
    print(f"\nheadroom captured over face-only: "
          f"{(v2_acc-face_acc)/(oracle-face_acc)*100:.1f}% of the available {(oracle-face_acc)*100:.2f} pp")

    out = args.out or f"fusion_v2_{'journal' if 'journal' in args.paired_set else 'goemotions'}.json"
    with open(os.path.join(_HERE, "results", out), "w") as f:
        json.dump({"paired_set": args.paired_set, "n_test": len(yt),
                   "temperature": {"text": T_text, "face": T_face},
                   "class_reliability": {"text": rel_t.tolist(), "face": rel_f.tolist()},
                   "strategies": rows, "oracle": oracle, "significance": sig}, f, indent=2)
    print(f"Saved -> research/results/{out}")


if __name__ == "__main__":
    main()
