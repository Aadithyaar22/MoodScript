"""Check that the SHIPPING fusion code reproduces the claimed accuracy.

eval_fusion_v2.py fits temperature and reliability on each paired set's own
calibration split. Production cannot do that — models/fusion.py carries one frozen
set of constants, fitted on the two calibration splits pooled
(research/fit_fusion_constants.py).

So the research number and the production number are not the same experiment, and
only this one is a claim about the deployed system. It imports models.fusion itself
and calls the real entry point, so it also catches the mundane failure where the
constants in the file do not match the ones that were fitted.

Also reports the legacy linear rule (MOODSCRIPT_LEGACY_FUSION=1) on the same split.
"""
import json
import os
import sys

import numpy as np
from sklearn.metrics import f1_score
from statsmodels.stats.contingency_tables import mcnemar

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, ".."))

UNIFIED = ["angry", "disgusted", "fearful", "happy", "neutral", "sad", "surprised"]


def run(layer, pairs):
    out = []
    for p in pairs:
        t = {"dominant_emotion": p["text_pred"], "all_scores": p["text_dist"],
             "confidence": max(p["text_dist"].values())}
        # the face service reports its label under "emotion", not "dominant_emotion"
        f = {"emotion": p["face_pred"], "all_scores": p["face_dist"],
             "confidence": max(p["face_dist"].values())}
        out.append(layer.fuse(t, f)["unified_emotion"])
    return out


def main():
    import models.fusion as fusion
    print(f"models/fusion.py  TEXT_TEMPERATURE={fusion.TEXT_TEMPERATURE}  "
          f"FACE_TEMPERATURE={fusion.FACE_TEMPERATURE}")

    fitted = os.path.join(_HERE, "results", "fusion_constants.json")
    if os.path.exists(fitted):
        c = json.load(open(fitted))
        drift = [k for k in UNIFIED
                 if abs(c["reliability"]["text"][k] - fusion.TEXT_RELIABILITY[k]) > 5e-4
                 or abs(c["reliability"]["face"][k] - fusion.FACE_RELIABILITY[k]) > 5e-4]
        t_ok = abs(c["temperature"]["text"] - fusion.TEXT_TEMPERATURE) <= 5e-4
        f_ok = abs(c["temperature"]["face"] - fusion.FACE_TEMPERATURE) <= 5e-4
        if drift or not (t_ok and f_ok):
            print(f"  !! MISMATCH vs fit_fusion_constants.py — temps ok: "
                  f"text={t_ok} face={f_ok}; drifted classes: {drift or 'none'}")
        else:
            print("  constants match research/results/fusion_constants.json")

    for name in ("paired_set.json", "paired_set_journal.json"):
        d = json.load(open(os.path.join(_HERE, "results", name)))
        tst = [p for p in d["pairs"] if p["split"] == "test"]
        y = [p["true"] for p in tst]
        print(f"\n=== {name}  (test n={len(tst)}) ===")

        preds = {"text only": [p["text_pred"] for p in tst],
                 "face only": [p["face_pred"] for p in tst],
                 "PRODUCTION log-linear": run(fusion.FusionLayer(), tst)}

        os.environ["MOODSCRIPT_LEGACY_FUSION"] = "1"
        import importlib
        importlib.reload(fusion)
        preds["legacy linear (env flag)"] = run(fusion.FusionLayer(), tst)
        del os.environ["MOODSCRIPT_LEGACY_FUSION"]
        importlib.reload(fusion)

        print(f"{'STRATEGY':<28}{'ACC %':>8}{'MACRO-F1':>10}")
        for k, p in preds.items():
            print(f"{k:<28}{np.mean([a == b for a, b in zip(p, y)])*100:>8.2f}"
                  f"{f1_score(y, p, average='macro', zero_division=0)*100:>10.2f}")

        for other in ("face only", "legacy linear (env flag)"):
            a = np.array([x == t for x, t in zip(preds["PRODUCTION log-linear"], y)])
            b = np.array([x == t for x, t in zip(preds[other], y)])
            n10, n01 = int((a & ~b).sum()), int((~a & b).sum())
            r = mcnemar([[int((a & b).sum()), n10], [n01, int((~a & ~b).sum())]],
                        exact=False, correction=True)
            print(f"  vs {other:<26} prod-only {n10:>3}, other-only {n01:>3}, "
                  f"p={r.pvalue:.4g} {'SIGNIFICANT' if r.pvalue < 0.05 else 'not significant'}")


if __name__ == "__main__":
    main()
