"""Benchmark the proposed fusion against the classical classifier combination rules.

WHY THESE BASELINES
-------------------
A reviewer will ask how this compares to named prior work rather than to variants the
authors invented. The end-to-end multimodal architectures (TFN, MulT, MISA) are not the
right comparison: they learn joint representations from raw sequences, whereas this is a
late-fusion rule over two probability distributions, and they are defined on tri-modal
sequence corpora (CMU-MOSEI, IEMOCAP) rather than text plus a single face crop.

The correct named prior art is the classical combination-rule family — sum, product, max
and min — analysed by Kittler, Hatef, Duin and Matas (1998). Those rules take exactly the
same input this system takes: two posterior distributions over a shared label set.

This matters because THE PROPOSED METHOD IS A WEIGHTED, CALIBRATED PRODUCT RULE. Running
the plain product rule alongside it isolates the actual contribution: not "we multiply
instead of averaging" (Kittler already established that), but "temperature calibration
plus class-conditional reliability weighting is what makes multiplying work here".

If the plain product rule matched the proposed method, the contribution would collapse to
a known result. That is the risk this script is designed to expose rather than hide.
"""
import argparse
import json
import os
import sys

import numpy as np
from sklearn.metrics import f1_score
from statsmodels.stats.contingency_tables import mcnemar

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, ".."))

from eval_fusion_v2 import (UNIFIED, IDX, vec, ts, fitT, ece,  # noqa: E402
                            class_reliability, TEXT_PRIOR, FACE_PRIOR)

EPS = 1e-12


def norm(P):
    s = P.sum(1, keepdims=True)
    s[s == 0] = 1.0
    return P / s


# ---- Kittler et al. (1998) combination rules, equal priors, two classifiers ----
def rule_sum(A, B):
    """Sum rule. Equivalent to averaging the posteriors."""
    return norm(A + B)


def rule_product(A, B):
    """Product rule. The unweighted, uncalibrated ancestor of the proposed method."""
    return norm(np.exp(np.log(np.clip(A, EPS, 1)) + np.log(np.clip(B, EPS, 1))))


def rule_max(A, B):
    return norm(np.maximum(A, B))


def rule_min(A, B):
    return norm(np.minimum(A, B))


def fuse_proposed(A, B, rel_t, rel_f):
    """Calibrated, class-conditionally weighted log-linear pooling (the paper's method)."""
    at = (rel_t[A.argmax(1)] * A.max(1))[:, None] * TEXT_PRIOR
    af = (rel_f[B.argmax(1)] * B.max(1))[:, None] * FACE_PRIOR
    tot = at + af
    tot[tot == 0] = 1.0
    at, af = at / tot, af / tot
    logp = at * np.log(np.clip(A, EPS, 1)) + af * np.log(np.clip(B, EPS, 1))
    logp -= logp.max(1, keepdims=True)
    return norm(np.exp(logp))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paired-set", default="paired_set.json")
    args = ap.parse_args()

    d = json.load(open(os.path.join(_HERE, "results", args.paired_set)))

    def pack(split):
        sub = [p for p in d["pairs"] if p["split"] == split]
        return (np.stack([vec(p["text_dist"]) for p in sub]),
                np.stack([vec(p["face_dist"]) for p in sub]),
                np.array([IDX[p["true"]] for p in sub]))

    Tc, Fc, yc = pack("calib")
    Tt, Ft, yt = pack("test")
    print(f"{args.paired_set}: calib={len(yc)} test={len(yt)}")

    # calibration and reliability are fitted on the calibration split only
    T_t, T_f = fitT(Tc, yc), fitT(Fc, yc)
    Tc_c, Fc_c = ts(Tc, T_t), ts(Fc, T_f)
    Tt_c, Ft_c = ts(Tt, T_t), ts(Ft, T_f)
    rel_t, rel_f = class_reliability(Tc_c, yc), class_reliability(Fc_c, yc)

    rows = []

    def add(name, P, note=""):
        pred = P.argmax(1)
        rows.append({"method": name, "note": note, "pred": pred,
                     "accuracy": float((pred == yt).mean()),
                     "macro_f1": float(f1_score(yt, pred, average="macro", zero_division=0)),
                     "ece": ece(P, yt)})

    add("Text only", Tt, "single modality")
    add("Face only", Ft, "single modality")
    # Classical rules on RAW posteriors — the form in which they are normally applied
    add("Sum rule [Kittler et al.]", rule_sum(Tt, Ft), "raw posteriors")
    add("Product rule [Kittler et al.]", rule_product(Tt, Ft), "raw posteriors")
    add("Max rule [Kittler et al.]", rule_max(Tt, Ft), "raw posteriors")
    add("Min rule [Kittler et al.]", rule_min(Tt, Ft), "raw posteriors")
    # The same rules AFTER calibration, to separate "calibration" from "which rule"
    add("Sum rule + calibration", rule_sum(Tt_c, Ft_c), "calibrated")
    add("Product rule + calibration", rule_product(Tt_c, Ft_c), "calibrated")
    # Baseline previously deployed, and the proposed method
    wt = TEXT_PRIOR * Tt.max(1, keepdims=True)
    wf = FACE_PRIOR * Ft.max(1, keepdims=True)
    tot = wt + wf
    tot[tot == 0] = 1
    add("Confidence-weighted linear (legacy)", (wt / tot) * Tt + (wf / tot) * Ft, "baseline")
    add("PROPOSED: calibrated log-linear", fuse_proposed(Tt_c, Ft_c, rel_t, rel_f),
        "this work")

    print(f"\n{'METHOD':<38}{'ACC %':>8}{'MACRO-F1':>10}{'ECE':>9}  NOTE")
    print("-" * 78)
    for r in rows:
        print(f"{r['method']:<38}{r['accuracy']*100:>8.2f}{r['macro_f1']*100:>10.2f}"
              f"{r['ece']:>9.4f}  {r['note']}")

    prop = next(r for r in rows if r["method"].startswith("PROPOSED"))
    print("\nMcNemar, proposed vs each baseline:")
    sig = {}
    for r in rows:
        if r is prop:
            continue
        a = prop["pred"] == yt
        b = r["pred"] == yt
        n10, n01 = int((a & ~b).sum()), int((~a & b).sum())
        res = mcnemar([[int((a & b).sum()), n10], [n01, int((~a & ~b).sum())]],
                      exact=False, correction=True)
        verdict = ("proposed better" if n10 > n01 else "baseline better") \
            if res.pvalue < 0.05 else "no significant difference"
        sig[r["method"]] = {"p": float(res.pvalue), "verdict": verdict,
                            "proposed_only": n10, "baseline_only": n01}
        print(f"  vs {r['method']:<36} p={res.pvalue:<11.4g} {verdict}")

    out = os.path.join(_HERE, "results",
                       f"classical_rules_{args.paired_set.replace('.json','')}.json")
    with open(out, "w") as f:
        json.dump({"paired_set": args.paired_set, "n_test": int(len(yt)),
                   "temperature": {"text": T_t, "face": T_f},
                   "rows": [{k: v for k, v in r.items() if k != "pred"} for r in rows],
                   "significance": sig}, f, indent=2)
    print(f"\nSaved -> {out}")


if __name__ == "__main__":
    main()
