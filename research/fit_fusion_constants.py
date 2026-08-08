"""Fit the production fusion constants in models/fusion.py and print them ready to paste.

WHY THIS IS A SCRIPT AND NOT AN AD-HOC SNIPPET
----------------------------------------------
The first time these constants were fitted, it was done interactively against a single
paired set — and that set (Set B, EmpatheticDialogues) contains NO neutral examples.
The resulting neutral reliability came out at 0.029 for text and 0.132 for face, purely
because there was nothing to estimate from. Shipping that would have made production
almost never predict neutral, which is plausibly the most common real-world label.

The fix is to pool the calibration splits of BOTH paired sets, so neutral has real
support. This file exists so that fix is permanent and reproducible rather than a thing
someone remembered to do once.

METHOD (identical to eval_fusion_v2.py, deliberately -- same helpers imported)
  1. pool the CALIBRATION splits of every paired set given (never the test splits)
  2. fit one temperature per modality by NLL minimisation
  3. compute Laplace-smoothed class-conditional reliability on the calibrated calib data

Test splits are never touched here. Evaluation happens in eval_fusion_v2.py.
"""
import argparse
import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from eval_fusion_v2 import UNIFIED, IDX, vec, ts, fitT, ece, class_reliability  # noqa: E402

# A class with fewer calibration predictions than this cannot support a meaningful
# reliability estimate; the run aborts rather than silently emitting a broken constant.
MIN_SUPPORT = 25


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paired-sets", nargs="+",
                    default=["paired_set.json", "paired_set_journal.json"])
    args = ap.parse_args()

    T_rows, F_rows, y_rows = [], [], []
    for name in args.paired_sets:
        d = json.load(open(os.path.join(_HERE, "results", name)))
        cal = [p for p in d["pairs"] if p["split"] == "calib"]
        print(f"{name}: {len(cal)} calibration pairs   [{d.get('text_pipeline','v1 text pipeline')}]")
        T_rows.append(np.stack([vec(p["text_dist"]) for p in cal]))
        F_rows.append(np.stack([vec(p["face_dist"]) for p in cal]))
        y_rows.append(np.array([IDX[p["true"]] for p in cal]))

    T, F, y = np.vstack(T_rows), np.vstack(F_rows), np.concatenate(y_rows)
    print(f"\npooled calibration set: n={len(y)}")

    support = {e: int((y == i).sum()) for i, e in enumerate(UNIFIED)}
    print("true-label support:", support)
    weak = [e for e, n in support.items() if n < MIN_SUPPORT]
    if weak:
        sys.exit(f"\nABORT: classes {weak} have < {MIN_SUPPORT} calibration examples. "
                 f"Pool in another paired set that contains them before fitting — "
                 f"see this file's docstring for why this guard exists.")

    T_text, T_face = fitT(T, y), fitT(F, y)
    Tc, Fc = ts(T, T_text), ts(F, T_face)
    rel_t, rel_f = class_reliability(Tc, y), class_reliability(Fc, y)

    print(f"\ntemperature      text {T_text:.4f}   face {T_face:.4f}")
    print(f"ECE (calib)      text {ece(T, y):.4f} -> {ece(Tc, y):.4f}   "
          f"face {ece(F, y):.4f} -> {ece(Fc, y):.4f}")
    print(f"\n{'class':<12}{'support':>9}{'text rel':>10}{'face rel':>10}")
    for c, e in enumerate(UNIFIED):
        print(f"{e:<12}{support[e]:>9}{rel_t[c]:>10.4f}{rel_f[c]:>10.4f}")

    print("\n" + "=" * 68)
    print("paste into models/fusion.py")
    print("=" * 68)
    print(f"TEXT_TEMPERATURE = {T_text:.4f}")
    print(f"FACE_TEMPERATURE = {T_face:.4f}")
    for nm, r in (("TEXT_RELIABILITY", rel_t), ("FACE_RELIABILITY", rel_f)):
        body = ", ".join(f'"{e}": {r[c]:.4f}' for c, e in enumerate(UNIFIED))
        print(f"{nm} = {{{body}}}")

    out = os.path.join(_HERE, "results", "fusion_constants.json")
    with open(out, "w") as f:
        json.dump({"paired_sets": args.paired_sets, "n_calib": int(len(y)),
                   "support": support,
                   "temperature": {"text": T_text, "face": T_face},
                   "reliability": {"text": {e: float(rel_t[c]) for c, e in enumerate(UNIFIED)},
                                   "face": {e: float(rel_f[c]) for c, e in enumerate(UNIFIED)}}},
                  f, indent=2)
    print(f"\nSaved -> {out}")


if __name__ == "__main__":
    main()
