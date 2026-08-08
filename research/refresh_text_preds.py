"""Re-run the current text pipeline over an existing paired set, in place.

WHY NOT JUST REBUILD
--------------------
build_paired_set.py would work, but it re-runs the FACE model over every image too
(~3,300 ViT forward passes on CPU) and re-samples the pairs. Neither is wanted here:
the face branch has not changed, and re-sampling would mean any measured difference in
fusion accuracy confounds "the text model improved" with "we drew different pairs".

This rewrites ONLY `text_dist` and `text_pred`. The pair list, the face distributions,
the calibration/test split assignment and the random seed all stay byte-identical, so a
before/after comparison isolates the text-pipeline change (see PAPER_BRIEF §6.2b).

The previous predictions are kept as `text_dist_v1` / `text_pred_v1` so the older
results remain reproducible from the same file.
"""
import argparse
import json
import os
import shutil
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "services", "text_service"))

UNIFIED = ["angry", "disgusted", "fearful", "happy", "neutral", "sad", "surprised"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paired-set", required=True)
    ap.add_argument("--no-backup", action="store_true")
    args = ap.parse_args()

    os.environ.setdefault("ENABLE_CLINICAL_TONE", "false")
    path = os.path.join(_HERE, "results", args.paired_set)
    data = json.load(open(path))
    pairs = data["pairs"]
    print(f"{args.paired_set}: {len(pairs)} pairs", flush=True)

    if not args.no_backup:
        bak = path + ".v1.bak"
        if not os.path.exists(bak):
            shutil.copy2(path, bak)
            print(f"backed up -> {os.path.basename(bak)}", flush=True)

    from text_model import EMOTION_MODEL, TextEmotionModel
    print(f"model: {EMOTION_MODEL}", flush=True)
    tm = TextEmotionModel()

    changed, t0 = 0, time.time()
    for i, p in enumerate(pairs):
        if i and i % 250 == 0:
            el = time.time() - t0
            print(f"  {i}/{len(pairs)}  {el/i*1000:.0f} ms/entry  "
                  f"eta {(len(pairs)-i)*el/i/60:.1f} min", flush=True)
        if "text_pred_v1" not in p:          # idempotent: keep the ORIGINAL v1, not the last run
            p["text_dist_v1"] = p["text_dist"]
            p["text_pred_v1"] = p["text_pred"]
        tr = tm.predict(p["text"])
        p["text_dist"] = {e: float(tr["all_scores"].get(e, 0.0)) for e in UNIFIED}
        p["text_pred"] = tr["dominant_emotion"]
        if p["text_pred"] != p["text_pred_v1"]:
            changed += 1

    acc1 = sum(1 for p in pairs if p["text_pred_v1"] == p["true"]) / len(pairs)
    acc2 = sum(1 for p in pairs if p["text_pred"] == p["true"]) / len(pairs)
    agree = sum(1 for p in pairs if p["text_pred"] == p["face_pred"])
    data["n_modalities_agree"] = agree
    data["text_pipeline"] = ("whole-entry classification, no negation dampening "
                             f"({EMOTION_MODEL})")

    with open(path, "w") as f:
        json.dump(data, f)

    print(f"\nlabels changed: {changed}/{len(pairs)}")
    print(f"text accuracy (all pairs): {acc1*100:.2f}% -> {acc2*100:.2f}%")
    print(f"modalities agree: {agree}/{len(pairs)} ({agree/len(pairs)*100:.1f}%) "
          f"-> {len(pairs)-agree} natural conflict cases")
    print(f"saved -> {path}")


if __name__ == "__main__":
    main()
