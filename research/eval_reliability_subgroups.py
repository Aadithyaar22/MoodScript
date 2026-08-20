"""Does class-conditional reliability weighting help anywhere, or nowhere?

CONTEXT
-------
eval_classical_rules.py showed that a temperature-calibrated version of Kittler's
product rule matches or beats the proposed method in aggregate: 92.03% vs 90.47% on
Set A (p=0.0265, in the baseline's favour) and 92.68% vs 92.83% on Set B (p=0.82).
That puts the reliability-weighting component of the contribution in question.

Aggregate accuracy can hide a real effect, though. Reliability weighting is designed to
act when the modalities disagree — when they agree, both rules pick the same class and
the weights are irrelevant. It could also matter disproportionately for classes where the
two modalities differ most in trustworthiness (text reliability spans 0.30-0.76; face
0.77-0.99).

So this asks two narrower questions than the headline number does:
  1. On CONFLICT cases only (text argmax != face argmax), does weighting help?
  2. PER CLASS, does weighting help anywhere, especially on the low-text-reliability
     classes it was designed for?

A negative answer here means the component should be dropped from the paper's claims.
A positive answer narrows the claim to a stated condition, which is still a contribution.
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

from eval_classical_rules import fuse_proposed, rule_product  # noqa: E402
from eval_fusion_v2 import (UNIFIED, IDX, vec, ts, fitT,  # noqa: E402
                            class_reliability)


def mc(a_ok, b_ok):
    n10, n01 = int((a_ok & ~b_ok).sum()), int((~a_ok & b_ok).sum())
    if n10 + n01 == 0:
        return n10, n01, 1.0
    r = mcnemar([[int((a_ok & b_ok).sum()), n10],
                 [n01, int((~a_ok & ~b_ok).sum())]], exact=False, correction=True)
    return n10, n01, float(r.pvalue)


def analyse(name):
    d = json.load(open(os.path.join(_HERE, "results", name)))

    def pack(split):
        sub = [p for p in d["pairs"] if p["split"] == split]
        return (np.stack([vec(p["text_dist"]) for p in sub]),
                np.stack([vec(p["face_dist"]) for p in sub]),
                np.array([IDX[p["true"]] for p in sub]))

    Tc, Fc, yc = pack("calib")
    Tt, Ft, yt = pack("test")
    T_t, T_f = fitT(Tc, yc), fitT(Fc, yc)
    Tc_c, Fc_c = ts(Tc, T_t), ts(Fc, T_f)
    Tt_c, Ft_c = ts(Tt, T_t), ts(Ft, T_f)
    rel_t, rel_f = class_reliability(Tc_c, yc), class_reliability(Fc_c, yc)

    prop = fuse_proposed(Tt_c, Ft_c, rel_t, rel_f).argmax(1)   # weighted
    base = rule_product(Tt_c, Ft_c).argmax(1)                  # unweighted, calibrated

    conflict = Tt.argmax(1) != Ft.argmax(1)
    print(f"\n{'='*74}\n{name}   test n={len(yt)}   "
          f"conflicts={int(conflict.sum())} ({conflict.mean()*100:.1f}%)\n{'='*74}")

    print("\n-- AGGREGATE --")
    print(f"  proposed (weighted)          {(prop==yt).mean()*100:6.2f}%")
    print(f"  calibrated product (unwtd)   {(base==yt).mean()*100:6.2f}%")

    print("\n-- CONFLICT CASES ONLY (where weighting can act at all) --")
    pc, bc, yc_ = prop[conflict], base[conflict], yt[conflict]
    n10, n01, p = mc(pc == yc_, bc == yc_)
    print(f"  proposed                     {(pc==yc_).mean()*100:6.2f}%  (n={len(yc_)})")
    print(f"  calibrated product           {(bc==yc_).mean()*100:6.2f}%")
    print(f"  proposed-only correct {n10}, baseline-only {n01}, p={p:.4g}"
          f"  -> {'SIGNIFICANT' if p < 0.05 else 'not significant'}")

    print("\n-- AGREEMENT CASES (sanity: rules should be identical) --")
    pa, ba, ya = prop[~conflict], base[~conflict], yt[~conflict]
    print(f"  proposed {(pa==ya).mean()*100:6.2f}%   product {(ba==ya).mean()*100:6.2f}%"
          f"   identical predictions: {bool((pa==ba).all())}")

    print("\n-- PER CLASS (recall on the test split) --")
    print(f"  {'class':<11}{'n':>5}{'text rel':>10}{'proposed':>10}{'product':>9}{'delta':>8}")
    deltas = {}
    for c, e in enumerate(UNIFIED):
        m = yt == c
        if not m.sum():
            continue
        rp, rb = (prop[m] == c).mean(), (base[m] == c).mean()
        deltas[e] = (rp - rb) * 100
        print(f"  {e:<11}{int(m.sum()):>5}{rel_t[c]:>10.3f}"
              f"{rp*100:>10.2f}{rb*100:>9.2f}{(rp-rb)*100:>+8.2f}")

    print(f"\n  macro-F1  proposed {f1_score(yt, prop, average='macro', zero_division=0)*100:.2f}"
          f"   product {f1_score(yt, base, average='macro', zero_division=0)*100:.2f}")

    # does the weighting help precisely where text is least reliable?
    order = sorted(deltas, key=lambda e: rel_t[IDX[e]])
    print("\n  classes ordered by TEXT reliability (lowest first), with recall delta:")
    print("   ", "  ".join(f"{e}({rel_t[IDX[e]]:.2f}):{deltas[e]:+.1f}" for e in order))
    return {"set": name, "n_test": int(len(yt)), "n_conflict": int(conflict.sum()),
            "conflict_proposed": float((pc == yc_).mean()),
            "conflict_product": float((bc == yc_).mean()),
            "conflict_p": p, "per_class_delta": deltas}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", nargs="+",
                    default=["paired_set.json", "paired_set_journal.json"])
    a = ap.parse_args()
    out = [analyse(s) for s in a.sets]
    p = os.path.join(_HERE, "results", "reliability_subgroups.json")
    json.dump(out, open(p, "w"), indent=2)
    print(f"\nSaved -> {p}")
