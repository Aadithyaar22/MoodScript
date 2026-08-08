"""Add the missing neutral class to the journal-domain paired set (Set B).

THE PROBLEM
-----------
Set B is built from EmpatheticDialogues, which has no neutral category. Every number
measured on it — text accuracy, the pipeline ablation, fusion accuracy — is therefore
computed on a benchmark that excludes the class both modalities are worst at (calibration
reliability: text 0.24, face 0.69, against 0.86-0.98 for every other class). It is also
plausibly the most common label in real journaling. A 7-class benchmark containing 6
classes overstates the system, and a reviewer will notice.

THE SOURCE
----------
DailyDialog utterances labelled "no emotion". The official repos (li2017dailydialog,
roskoN) ship loading scripts, which recent `datasets` refuses to execute, so this uses
the parquet mirror `pixelsandpointers/better_daily_dialog`.

Utterances are filtered to >= MIN_WORDS so the register sits closer to the
EmpatheticDialogues situations already in the set (mean 22.4 words; unfiltered
DailyDialog averages 13.8). This narrows the gap but does not close it: DailyDialog is
dialogue turns, EmpatheticDialogues is first-person narrative. THAT MISMATCH MUST BE
DISCLOSED IN THE PAPER — it is a real caveat, not a detail.

WHY APPEND RATHER THAN REBUILD
------------------------------
Existing pairs keep their text, face distributions and calib/test assignment untouched,
so every previously reported number stays reproducible from the same file and the
before/after comparison isolates exactly one change: the presence of neutral.
"""
import argparse
import json
import os
import random
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "services", "text_service"))

UNIFIED = ["angry", "disgusted", "fearful", "happy", "neutral", "sad", "surprised"]
FER2013_LABELS = ["angry", "disgusted", "fearful", "happy", "neutral", "sad", "surprised"]
MIN_WORDS = 18

# DailyDialog tokenises punctuation with surrounding spaces ("Say , Jim , how about ...").
# Left alone it is a visible domain artefact the classifier never sees in production, so
# it is normalised back to ordinary English spacing.
def detokenise(s: str) -> str:
    s = re.sub(r"\s+([,.!?;:'])", r"\1", s)
    s = re.sub(r"\s+n't\b", "n't", s)
    s = re.sub(r"\s{2,}", " ", s)
    return s.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paired-set", default="paired_set_journal.json")
    ap.add_argument("--n", type=int, default=400, help="neutral pairs to add")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    random.seed(args.seed)

    os.environ.setdefault("ENABLE_CLINICAL_TONE", "false")
    from datasets import load_dataset
    from transformers import pipeline
    from text_model import TextEmotionModel

    path = os.path.join(_HERE, "results", args.paired_set)
    data = json.load(open(path))
    pairs = data["pairs"]
    if any(p["true"] == "neutral" for p in pairs):
        sys.exit("This set already contains neutral pairs — nothing to do.")
    print(f"{args.paired_set}: {len(pairs)} pairs, no neutral class", flush=True)

    # ---------- neutral texts ----------
    print("loading DailyDialog (parquet mirror)...", flush=True)
    dd = load_dataset("pixelsandpointers/better_daily_dialog", split="train")
    seen, texts = set(), []
    for u, e in zip(dd["utterance"], dd["emotion"]):
        if e != 0:
            continue                       # 0 == "no emotion"
        t = detokenise(u or "")
        if len(t.split()) >= MIN_WORDS and t not in seen:
            seen.add(t)
            texts.append(t)
    print(f"  neutral candidates >= {MIN_WORDS} words: {len(texts)}", flush=True)
    if len(texts) < args.n:
        sys.exit(f"only {len(texts)} candidates for {args.n} pairs")
    texts = random.sample(texts, args.n)

    # ---------- neutral faces ----------
    print("loading FER2013 test split...", flush=True)
    ds_f = load_dataset("clip-benchmark/wds_fer2013", split="test")
    neutral_idx = [i for i, c in enumerate(ds_f["cls"]) if FER2013_LABELS[c] == "neutral"]
    print(f"  neutral face images: {len(neutral_idx)}", flush=True)
    faces = random.sample(neutral_idx, args.n)

    # ---------- run both models ----------
    print("loading models...", flush=True)
    tm = TextEmotionModel()
    fpipe = pipeline("image-classification",
                     model="dima806/facial_emotions_image_detection",
                     top_k=None, device=-1)
    FACE_MAP = {"angry": "angry", "disgust": "disgusted", "fear": "fearful",
                "happy": "happy", "neutral": "neutral", "sad": "sad",
                "surprise": "surprised"}

    new = []
    for i, (t, fi) in enumerate(zip(texts, faces)):
        if i and i % 50 == 0:
            print(f"  {i}/{args.n}", flush=True)
        tr = tm.predict(t)
        raw = fpipe(ds_f[fi]["jpg"].convert("RGB"))
        fd = {e: 0.0 for e in UNIFIED}
        for r in raw:
            fd[FACE_MAP.get(r["label"].lower(), "neutral")] += float(r["score"])
        s = sum(fd.values()) or 1.0
        fd = {e: v / s for e, v in fd.items()}
        new.append({
            "true": "neutral", "text": t, "face_idx": fi,
            "text_dist": {e: float(tr["all_scores"].get(e, 0.0)) for e in UNIFIED},
            "text_pred": tr["dominant_emotion"],
            "face_dist": fd, "face_pred": max(fd, key=fd.get),
        })

    # ---------- stratified split over the NEW pairs only ----------
    random.shuffle(new)
    half = len(new) // 2
    for p in new[:half]:
        p["split"] = "calib"
    for p in new[half:]:
        p["split"] = "test"

    t_acc = sum(1 for p in new if p["text_pred"] == "neutral") / len(new)
    f_acc = sum(1 for p in new if p["face_pred"] == "neutral") / len(new)
    print(f"\non the {len(new)} new neutral pairs:")
    print(f"  text  predicts neutral {t_acc*100:.1f}% of the time")
    print(f"  face  predicts neutral {f_acc*100:.1f}% of the time")

    pairs.extend(new)
    data["n_pairs"] = len(pairs)
    data["n_calib"] = sum(1 for p in pairs if p["split"] == "calib")
    data["n_test"] = len(pairs) - data["n_calib"]
    data["n_modalities_agree"] = sum(1 for p in pairs if p["text_pred"] == p["face_pred"])
    data["neutral_source"] = (
        f"DailyDialog 'no emotion' utterances via pixelsandpointers/better_daily_dialog, "
        f">= {MIN_WORDS} words, de-duplicated, punctuation de-tokenised. NOTE: dialogue "
        f"turns, not first-person narrative like the rest of this set — disclose in paper.")
    with open(path, "w") as f:
        json.dump(data, f)

    print(f"\nSet B now {len(pairs)} pairs, all 7 classes")
    print(f"  calib={data['n_calib']}  test={data['n_test']}")
    print(f"saved -> {path}")


if __name__ == "__main__":
    main()
