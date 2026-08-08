"""Quantifies the LLM arbitration layer on real conflict cases.

The arbitration layer was previously claimed as a contribution with no measurement
attached. This evaluates it on the subset of the paired set where the layer would
actually fire in production — i.e. where fusion reports `conflict_resolved_to_*`
(both modalities disagree at comparable confidence) — and where ground truth is
known from the pair's shared source label.

Reported baselines on that same subset, so the arbiter is judged against the
alternatives it replaces rather than in isolation:
    - numeric fusion (what arbitration overrides)
    - text only
    - face only
    - always-pick-text  (a trivial policy, since text is the primary modality)
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from models.fusion import FusionLayer  # noqa: E402

UNIFIED = ["angry", "disgusted", "fearful", "happy", "neutral", "sad", "surprised"]
_HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    import asyncio
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_HERE, "..", ".env"))
    from models.arbiter import Arbiter

    data = json.load(open(os.path.join(_HERE, "results", "paired_set.json")))
    pairs = [p for p in data["pairs"] if p["split"] == "test"]
    fusion = FusionLayer()
    arbiter = Arbiter()

    # Reproduce production shapes and find the cases where arbitration fires.
    conflicts = []
    for p in pairs:
        tr = {"dominant_emotion": p["text_pred"],
              "confidence": max(p["text_dist"].values()),
              "all_scores": p["text_dist"]}
        fr = {"emotion": p["face_pred"],
              "confidence": max(p["face_dist"].values()),
              "all_scores": p["face_dist"]}
        fused = fusion.fuse(tr, fr)
        if arbiter.should_arbitrate(fused):
            conflicts.append((p, tr, fr, fused))

    print(f"test pairs: {len(pairs)}")
    print(f"arbitration fires on: {len(conflicts)} ({len(conflicts)/len(pairs)*100:.1f}%)")
    if not conflicts:
        print("no conflict cases — nothing to evaluate")
        return

    async def run():
        out = []
        for i, (p, tr, fr, fused) in enumerate(conflicts):
            if i % 10 == 0:
                print(f"  arbitrating {i}/{len(conflicts)}")
            res = await arbiter.arbitrate(p["text"], tr, fr, dict(fused))
            out.append(res["unified_emotion"])
        return out

    arb_preds = asyncio.run(run())

    y = [p["true"] for p, _, _, _ in conflicts]
    fusion_preds = [f["unified_emotion"] for _, _, _, f in conflicts]
    text_preds = [p["text_pred"] for p, _, _, _ in conflicts]
    face_preds = [p["face_pred"] for p, _, _, _ in conflicts]

    def acc(preds):
        return float(np.mean([a == b for a, b in zip(preds, y)]))

    rows = [
        ("LLM arbitration (proposed)", acc(arb_preds)),
        ("numeric fusion (what it overrides)", acc(fusion_preds)),
        ("text only", acc(text_preds)),
        ("face only", acc(face_preds)),
    ]
    print(f"\nACCURACY ON CONFLICT CASES (n={len(conflicts)})")
    print(f"{'method':<40}{'acc %':>8}")
    print("-" * 48)
    for name, a in rows:
        print(f"{name:<40}{a*100:>8.2f}")

    changed = sum(1 for a, f in zip(arb_preds, fusion_preds) if a != f)
    helped = sum(1 for a, f, t in zip(arb_preds, fusion_preds, y) if a != f and a == t)
    hurt = sum(1 for a, f, t in zip(arb_preds, fusion_preds, y) if a != f and f == t)
    print(f"\narbiter changed the label on {changed}/{len(conflicts)} conflict cases")
    print(f"  changed and became correct : {helped}")
    print(f"  changed and became wrong   : {hurt}")
    print(f"  net                        : {helped - hurt:+d}")

    path = os.path.join(_HERE, "results", "arbiter_paired.json")
    with open(path, "w") as f:
        json.dump({
            "n_test_pairs": len(pairs),
            "n_conflicts": len(conflicts),
            "conflict_rate": len(conflicts) / len(pairs),
            "accuracy": {n: a for n, a in rows},
            "changed": changed, "helped": helped, "hurt": hurt,
            "net": helped - hurt,
            "cases": [
                {"text": p["text"][:200], "true": p["true"],
                 "text_pred": p["text_pred"], "face_pred": p["face_pred"],
                 "fusion": fp, "arbiter": ap}
                for (p, _, _, _), fp, ap in zip(conflicts, fusion_preds, arb_preds)
            ],
        }, f, indent=2, ensure_ascii=False)
    print(f"\nSaved -> {path}")


if __name__ == "__main__":
    main()
