"""Fusion strategy comparison on the paired text+face set.

Compares, on identical pairs:
  1. text only
  2. face only
  3. naive fixed-weight fusion            (0.55 / 0.45, no confidence term)
  4. confidence-weighted fusion           (the currently deployed method)
  5. calibrated confidence-weighted fusion (proposed)

WHY 5 EXISTS
------------
Measured on the existing benchmarks, the two modalities' confidence scores are not
on a comparable scale:

    text  ECE = 0.225   (says 0.66, is right 0.44 of the time)
    face  ECE = 0.015   (says 0.87, is right 0.88 of the time)

Method 4 multiplies each modality's prior by that raw confidence, so it is combining
two numbers that do not mean the same thing, and systematically over-trusts the
badly-calibrated modality. Method 5 first maps each modality's scores onto a common,
honest scale with temperature scaling, then applies the same confidence weighting.

Temperature is fitted on the calibration split ONLY and every number reported below
comes from the held-out test split.
"""
import argparse
import json
import os

import numpy as np
from scipy.optimize import minimize_scalar
from sklearn.metrics import f1_score
from statsmodels.stats.contingency_tables import mcnemar

UNIFIED = ["angry", "disgusted", "fearful", "happy", "neutral", "sad", "surprised"]
IDX = {e: i for i, e in enumerate(UNIFIED)}
TEXT_PRIOR, FACE_PRIOR = 0.55, 0.45
_HERE = os.path.dirname(os.path.abspath(__file__))


def vec(dist):
    v = np.array([dist[e] for e in UNIFIED], dtype=float)
    s = v.sum()
    return v / s if s > 0 else np.full(len(UNIFIED), 1 / len(UNIFIED))


def temperature_scale(P, T):
    """Apply temperature T to probability rows. Recovers pseudo-logits via log(p),
    divides by T, re-softmaxes. T>1 softens (less confident), T<1 sharpens."""
    logits = np.log(np.clip(P, 1e-12, 1.0)) / T
    logits -= logits.max(axis=1, keepdims=True)
    e = np.exp(logits)
    return e / e.sum(axis=1, keepdims=True)


def fit_temperature(P, y):
    """Fit T minimising negative log-likelihood of the true class."""
    def nll(T):
        if T <= 0:
            return 1e9
        Q = temperature_scale(P, T)
        return float(-np.mean(np.log(np.clip(Q[np.arange(len(y)), y], 1e-12, 1.0))))
    r = minimize_scalar(nll, bounds=(0.05, 20.0), method="bounded")
    return float(r.x)


def ece(P, y, n_bins=10):
    conf = P.max(axis=1)
    pred = P.argmax(axis=1)
    corr = (pred == y).astype(float)
    bins = np.linspace(0, 1, n_bins + 1)
    out = 0.0
    for lo, hi in zip(bins[:-1], bins[1:]):
        m = (conf > lo) & (conf <= hi)
        if m.sum():
            out += m.sum() / len(conf) * abs(conf[m].mean() - corr[m].mean())
    return float(out)


def fuse(Tp, Fp, weighted=True):
    """Row-wise fusion. weighted=False -> fixed priors (naive)."""
    if weighted:
        wt = TEXT_PRIOR * Tp.max(axis=1, keepdims=True)
        wf = FACE_PRIOR * Fp.max(axis=1, keepdims=True)
        tot = wt + wf
        tot[tot == 0] = 1.0
        wt, wf = wt / tot, wf / tot
    else:
        wt, wf = TEXT_PRIOR, FACE_PRIOR
    return wt * Tp + wf * Fp


def report(name, P, y, rows):
    pred = P.argmax(axis=1)
    acc = float((pred == y).mean())
    f1 = float(f1_score(y, pred, average="macro", zero_division=0))
    e = ece(P, y)
    rows.append({"strategy": name, "accuracy": acc, "macro_f1": f1, "ece": e})
    print(f"{name:<42}{acc*100:>8.2f}{f1*100:>10.2f}{e:>9.4f}")
    return pred


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paired-set", default="paired_set.json")
    ap.add_argument("--out", default="fusion_paired.json")
    args = ap.parse_args()

    data = json.load(open(os.path.join(_HERE, "results", args.paired_set)))
    print(f"paired set: {args.paired_set}  ({data.get('text_source','?')})")
    pairs = data["pairs"]

    def pack(split):
        sub = [p for p in pairs if p["split"] == split]
        Tp = np.stack([vec(p["text_dist"]) for p in sub])
        Fp = np.stack([vec(p["face_dist"]) for p in sub])
        y = np.array([IDX[p["true"]] for p in sub])
        return sub, Tp, Fp, y

    cal, Tc, Fc, yc = pack("calib")
    tst, Tt, Ft, yt = pack("test")
    print(f"pairs: {len(pairs)}  calib={len(cal)}  test={len(tst)}")

    # ---- fit temperatures on the calibration split only ----
    T_text = fit_temperature(Tc, yc)
    T_face = fit_temperature(Fc, yc)
    print(f"\nfitted temperature  text T={T_text:.3f}   face T={T_face:.3f}")
    print("(T>1 softens an overconfident model; T~1 means already calibrated)")

    print(f"\ncalibration on TEST split (ECE):")
    print(f"  text  raw={ece(Tt,yt):.4f}  ->  calibrated={ece(temperature_scale(Tt,T_text),yt):.4f}")
    print(f"  face  raw={ece(Ft,yt):.4f}  ->  calibrated={ece(temperature_scale(Ft,T_face),yt):.4f}")

    Tt_c = temperature_scale(Tt, T_text)
    Ft_c = temperature_scale(Ft, T_face)

    # Averaging two distributions flattens the peak, so the fused output ends up
    # UNDER-confident even when both inputs are calibrated. A third temperature,
    # fitted on the fused calibration-split output, corrects that. It is monotone,
    # so it cannot change the predicted label — only the confidence attached to it.
    T_fused = fit_temperature(fuse(temperature_scale(Tc, T_text),
                                   temperature_scale(Fc, T_face), weighted=True), yc)
    print(f"post-fusion temperature T={T_fused:.3f}")

    print(f"\n{'STRATEGY':<42}{'ACC %':>8}{'MACRO-F1':>10}{'ECE':>9}")
    print("-" * 69)
    rows = []
    report("text only", Tt, yt, rows)
    pred_face = report("face only", Ft, yt, rows)
    report("naive fixed-weight fusion", fuse(Tt, Ft, weighted=False), yt, rows)
    pred_deployed = report("confidence-weighted fusion (deployed)", fuse(Tt, Ft, weighted=True), yt, rows)
    P_cal = fuse(Tt_c, Ft_c, weighted=True)
    pred_calib = report("calibrated confidence-weighted (proposed)", P_cal, yt, rows)
    report("  + post-fusion calibration", temperature_scale(P_cal, T_fused), yt, rows)

    def paired(name, a_pred, b_pred, label_a, label_b):
        a = a_pred == yt
        b = b_pred == yt
        n10, n01 = int((a & ~b).sum()), int((~a & b).sum())
        r = mcnemar([[int((a & b).sum()), n10], [n01, int((~a & ~b).sum())]],
                    exact=False, correction=True)
        verdict = "SIGNIFICANT" if r.pvalue < 0.05 else "NOT significant"
        print(f"\nMcNemar — {name} (n={len(yt)})")
        print(f"  {label_a} only correct = {n10}")
        print(f"  {label_b} only correct = {n01}")
        print(f"  chi2={r.statistic:.3f}  p={r.pvalue:.4g}  -> {verdict}")
        return {"n_a_only": n10, "n_b_only": n01,
                "chi2": float(r.statistic), "p_value": float(r.pvalue),
                "significant": bool(r.pvalue < 0.05)}

    sig_vs_deployed = paired("calibrated vs deployed", pred_calib, pred_deployed,
                             "calibrated", "deployed")
    # The honest control: does fusion actually beat the stronger single modality?
    sig_vs_face = paired("calibrated vs face-only", pred_calib, pred_face,
                         "calibrated", "face-only")

    out = {
        "n_pairs": len(pairs), "n_calib": len(cal), "n_test": len(tst),
        "temperature": {"text": T_text, "face": T_face, "fused": T_fused},
        "ece_test": {
            "text_raw": ece(Tt, yt), "text_calibrated": ece(Tt_c, yt),
            "face_raw": ece(Ft, yt), "face_calibrated": ece(Ft_c, yt),
        },
        "strategies": rows,
        "mcnemar_calibrated_vs_deployed": sig_vs_deployed,
        "mcnemar_calibrated_vs_face_only": sig_vs_face,
    }
    path = os.path.join(_HERE, "results", args.out)
    with open(path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nSaved -> {path}")


if __name__ == "__main__":
    main()
