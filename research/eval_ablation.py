"""Ablation over the fusion pipeline's components, on the paired test split.

Every row reuses the cached predictions in paired_set.json, so the ablation costs
no inference. Temperatures are always fitted on the calibration split only.

Components:
  TC  text calibration      (temperature scaling on the text distribution)
  FC  face calibration      (temperature scaling on the face distribution)
  CW  confidence weighting  (scale each prior by that modality's own confidence)
  PC  post-fusion calibration (temperature on the fused output)
"""
import itertools
import json
import os

import numpy as np
from scipy.optimize import minimize_scalar
from sklearn.metrics import f1_score

UNIFIED = ["angry", "disgusted", "fearful", "happy", "neutral", "sad", "surprised"]
IDX = {e: i for i, e in enumerate(UNIFIED)}
TEXT_PRIOR, FACE_PRIOR = 0.55, 0.45
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


def ece(P, y, nb=10):
    c, a = P.max(1), (P.argmax(1) == y).astype(float)
    b = np.linspace(0, 1, nb + 1)
    o = 0.0
    for lo, hi in zip(b[:-1], b[1:]):
        m = (c > lo) & (c <= hi)
        if m.sum():
            o += m.sum() / len(c) * abs(c[m].mean() - a[m].mean())
    return float(o)


def fuse(A, B, weighted):
    if weighted:
        wt, wf = TEXT_PRIOR * A.max(1, keepdims=True), FACE_PRIOR * B.max(1, keepdims=True)
        t = wt + wf
        t[t == 0] = 1
        wt, wf = wt / t, wf / t
    else:
        wt, wf = TEXT_PRIOR, FACE_PRIOR
    return wt * A + wf * B


def main():
    data = json.load(open(os.path.join(_HERE, "results", "paired_set.json")))

    def pack(s):
        sub = [p for p in data["pairs"] if p["split"] == s]
        return (np.stack([vec(p["text_dist"]) for p in sub]),
                np.stack([vec(p["face_dist"]) for p in sub]),
                np.array([IDX[p["true"]] for p in sub]))

    Tc, Fc, yc = pack("calib")
    Tt, Ft, yt = pack("test")
    T_text, T_face = fitT(Tc, yc), fitT(Fc, yc)

    print(f"{'TC':>3}{'FC':>4}{'CW':>4}{'PC':>4}{'ACC %':>9}{'MACRO-F1':>10}{'ECE':>9}")
    print("-" * 43)
    rows = []
    for tc, fc, cw, pc in itertools.product([0, 1], repeat=4):
        A = ts(Tt, T_text) if tc else Tt
        B = ts(Ft, T_face) if fc else Ft
        Acal = ts(Tc, T_text) if tc else Tc
        Bcal = ts(Fc, T_face) if fc else Fc
        P = fuse(A, B, bool(cw))
        if pc:
            T_post = fitT(fuse(Acal, Bcal, bool(cw)), yc)
            P = ts(P, T_post)
        pred = P.argmax(1)
        acc = float((pred == yt).mean())
        f1 = float(f1_score(yt, pred, average="macro", zero_division=0))
        e = ece(P, yt)
        mark = lambda b: " Y" if b else " ."
        print(f"{mark(tc):>3}{mark(fc):>4}{mark(cw):>4}{mark(pc):>4}{acc*100:>9.2f}{f1*100:>10.2f}{e:>9.4f}")
        rows.append({"text_calibration": bool(tc), "face_calibration": bool(fc),
                     "confidence_weighting": bool(cw), "post_fusion_calibration": bool(pc),
                     "accuracy": acc, "macro_f1": f1, "ece": e})

    best_acc = max(rows, key=lambda r: r["accuracy"])
    best_ece = min(rows, key=lambda r: r["ece"])
    print(f"\nbest accuracy : {best_acc['accuracy']*100:.2f}%  "
          f"(TC={best_acc['text_calibration']}, FC={best_acc['face_calibration']}, "
          f"CW={best_acc['confidence_weighting']}, PC={best_acc['post_fusion_calibration']})")
    print(f"best ECE      : {best_ece['ece']:.4f}  "
          f"(TC={best_ece['text_calibration']}, FC={best_ece['face_calibration']}, "
          f"CW={best_ece['confidence_weighting']}, PC={best_ece['post_fusion_calibration']})")

    # marginal effect of each component, averaged over all settings of the others
    print("\nmarginal effect (mean over all other settings):")
    for key, label in [("text_calibration", "text calibration"),
                       ("face_calibration", "face calibration"),
                       ("confidence_weighting", "confidence weighting"),
                       ("post_fusion_calibration", "post-fusion calibration")]:
        on = np.mean([r["accuracy"] for r in rows if r[key]])
        off = np.mean([r["accuracy"] for r in rows if not r[key]])
        one = np.mean([r["ece"] for r in rows if r[key]])
        oe = np.mean([r["ece"] for r in rows if not r[key]])
        print(f"  {label:<26} accuracy {(on-off)*100:+6.2f} pp    ECE {one-oe:+.4f}")

    path = os.path.join(_HERE, "results", "ablation.json")
    with open(path, "w") as f:
        json.dump({"temperature": {"text": T_text, "face": T_face},
                   "n_test": len(yt), "rows": rows}, f, indent=2)
    print(f"\nSaved -> {path}")


if __name__ == "__main__":
    main()
