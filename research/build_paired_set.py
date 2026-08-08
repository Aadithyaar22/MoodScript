"""Builds a paired text+face evaluation set for the fusion experiments.

WHY THIS EXISTS
---------------
The fusion layer was previously only checked against 8 hand-written scenarios, which
cannot support any claim about accuracy. No public dataset provides paired
journal-text + facial-image emotion labels, so this constructs one.

CONSTRUCTION (the important methodological choice)
--------------------------------------------------
Pairs are CONGRUENT: a GoEmotions text labelled X is paired with a FER2013 image
labelled X, so the ground truth of the pair is unambiguously X.

Disagreement between the modalities is therefore NOT synthesised — it arises
naturally when one of the two models is simply wrong. That is precisely the
situation fusion is supposed to repair, and it keeps the benchmark non-circular:
we never have to declare which modality "should" win a manufactured conflict.

Both models' FULL 7-class probability distributions are cached, so every downstream
experiment (naive vs confidence-weighted vs calibrated fusion, arbitration,
ablations) reuses these predictions instead of re-running inference.

The set is split into a calibration half and a test half, stratified by label.
Temperature scaling is fitted ONLY on the calibration split and evaluated ONLY on
the test split — calibrating and evaluating on the same data would be invalid.
"""
import argparse
import json
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                                "services", "text_service"))

UNIFIED = ["angry", "disgusted", "fearful", "happy", "neutral", "sad", "surprised"]
FER2013_LABELS = ["angry", "disgusted", "fearful", "happy", "neutral", "sad", "surprised"]

EKMAN_MAPPING = {
    "anger": ["anger", "annoyance", "disapproval"],
    "disgust": ["disgust"],
    "fear": ["fear", "nervousness"],
    "joy": ["joy", "amusement", "approval", "excitement", "gratitude", "love",
            "optimism", "relief", "pride", "admiration", "desire", "caring"],
    "sadness": ["sadness", "disappointment", "embarrassment", "grief", "remorse"],
    "surprise": ["surprise", "realization", "confusion", "curiosity"],
}
EKMAN_TO_UNIFIED = {"anger": "angry", "disgust": "disgusted", "fear": "fearful",
                    "joy": "happy", "sadness": "sad", "surprise": "surprised"}


def build_fine_to_unified(label_names):
    fine_to_ekman = {f: e for e, fines in EKMAN_MAPPING.items() for f in fines}
    out = {}
    for i, name in enumerate(label_names):
        if name == "neutral":
            out[i] = "neutral"
        elif name in fine_to_ekman:
            out[i] = EKMAN_TO_UNIFIED[fine_to_ekman[name]]
        else:
            out[i] = None
    return out


# EmpatheticDialogues "situation" text is first-person emotional narrative
# ("I felt guilty when I was driving home one night and..."), averaging 22.4 words
# against GoEmotions' 12.9 — far closer to a journal entry than a Reddit comment.
# Only unambiguous emotions are mapped; anything whose mapping would be a judgement
# call (nostalgic, sentimental, guilty, jealous, caring, anticipating, ...) is
# DROPPED rather than forced, so the pair's ground truth stays clean.
EMPATHETIC_TO_UNIFIED = {
    "angry": "angry", "furious": "angry", "annoyed": "angry",
    "disgusted": "disgusted",
    "afraid": "fearful", "terrified": "fearful", "anxious": "fearful",
    "apprehensive": "fearful",
    "joyful": "happy", "excited": "happy", "proud": "happy",
    "grateful": "happy", "content": "happy", "hopeful": "happy",
    "sad": "sad", "devastated": "sad", "disappointed": "sad", "lonely": "sad",
    "surprised": "surprised",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-class", type=int, default=200,
                    help="pairs per emotion class (7 classes)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--text-source", choices=["goemotions", "empathetic"],
                    default="goemotions",
                    help="goemotions = short Reddit comments; empathetic = first-person "
                         "narrative situations, much closer to journal writing")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                  "results", "paired_set.json"))
    args = ap.parse_args()
    random.seed(args.seed)

    from datasets import load_dataset
    from transformers import pipeline
    from PIL import Image
    from text_model import TextEmotionModel

    # ---------- collect texts by unified label ----------
    texts = {e: [] for e in UNIFIED}
    if args.text_source == "goemotions":
        print("Loading GoEmotions test split...")
        ds_t = load_dataset("go_emotions", "simplified", split="test")
        f2u = build_fine_to_unified(ds_t.features["labels"].feature.names)
        for ex in ds_t:
            if len(ex["labels"]) != 1:
                continue                  # single-label only, keeps ground truth clean
            u = f2u.get(ex["labels"][0])
            if u:
                texts[u].append(ex["text"])
        text_source_desc = "GoEmotions test split (single-label, Ekman-mapped)"
    else:
        print("Loading EmpatheticDialogues situations...")
        ds_t = load_dataset("bdotloh/empathetic-dialogues-contexts", split="test")
        for ex in ds_t:
            u = EMPATHETIC_TO_UNIFIED.get(ex["emotion"])
            if u:
                texts[u].append(ex["situation"])
        text_source_desc = ("EmpatheticDialogues situations (first-person narrative; "
                            "ambiguous emotions dropped, no neutral class available)")
    print("  texts available:", {k: len(v) for k, v in texts.items()})

    # ---------- collect face images by unified label (FER2013 test) ----------
    print("Loading FER2013 test split...")
    ds_f = load_dataset("clip-benchmark/wds_fer2013", split="test")
    faces = {e: [] for e in UNIFIED}
    for i, ex in enumerate(ds_f):
        faces[FER2013_LABELS[ex["cls"]]].append(i)
    print("  faces available:", {k: len(v) for k, v in faces.items()})

    # ---------- sample congruent pairs ----------
    pairs = []
    for e in UNIFIED:
        n = min(args.per_class, len(texts[e]), len(faces[e]))
        if n < args.per_class:
            print(f"  ! {e}: only {n} pairs available (wanted {args.per_class})")
        ts = random.sample(texts[e], n)
        fs = random.sample(faces[e], n)
        for t, fi in zip(ts, fs):
            pairs.append({"true": e, "text": t, "face_idx": fi})
    random.shuffle(pairs)
    print(f"\nBuilt {len(pairs)} congruent pairs")

    # ---------- run both models, caching FULL distributions ----------
    print("Loading text model...")
    tmodel = TextEmotionModel()
    print("Loading face model...")
    fpipe = pipeline("image-classification",
                     model="dima806/facial_emotions_image_detection",
                     top_k=None, device=-1)
    FACE_LABEL_MAP = {"angry": "angry", "disgust": "disgusted", "fear": "fearful",
                      "happy": "happy", "neutral": "neutral", "sad": "sad",
                      "surprise": "surprised"}

    for i, p in enumerate(pairs):
        if i % 100 == 0:
            print(f"  {i}/{len(pairs)}")
        tr = tmodel.predict(p["text"])
        p["text_dist"] = {e: float(tr["all_scores"].get(e, 0.0)) for e in UNIFIED}
        p["text_pred"] = tr["dominant_emotion"]

        img = ds_f[p["face_idx"]]["jpg"].convert("RGB")
        raw = fpipe(img)
        fd = {e: 0.0 for e in UNIFIED}
        for r in raw:
            fd[FACE_LABEL_MAP.get(r["label"].lower(), "neutral")] += float(r["score"])
        s = sum(fd.values()) or 1.0
        p["face_dist"] = {e: v / s for e, v in fd.items()}
        p["face_pred"] = max(p["face_dist"], key=p["face_dist"].get)

    # ---------- stratified calibration / test split ----------
    by_label = {}
    for p in pairs:
        by_label.setdefault(p["true"], []).append(p)
    for e, group in by_label.items():
        random.shuffle(group)
        half = len(group) // 2
        for p in group[:half]:
            p["split"] = "calib"
        for p in group[half:]:
            p["split"] = "test"

    n_cal = sum(1 for p in pairs if p["split"] == "calib")
    agree = sum(1 for p in pairs if p["text_pred"] == p["face_pred"])
    out = {
        "description": "Congruent text+face pairs; ground truth = shared source label. "
                       "Disagreement arises from model error, not synthetic conflict.",
        "seed": args.seed,
        "n_pairs": len(pairs),
        "n_calib": n_cal,
        "n_test": len(pairs) - n_cal,
        "n_modalities_agree": agree,
        "text_source": text_source_desc,
        "face_source": "FER2013 test split (clip-benchmark/wds_fer2013)",
        "pairs": pairs,
    }
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(out, f)
    print(f"\nSaved {len(pairs)} pairs -> {args.out}")
    print(f"  calib={n_cal}  test={len(pairs)-n_cal}")
    print(f"  modalities agree on {agree}/{len(pairs)} ({agree/len(pairs)*100:.1f}%) "
          f"-> {len(pairs)-agree} natural conflict cases")


if __name__ == "__main__":
    main()
