"""
Compares naive fixed-weight fusion (55% text / 45% face, always) against the new
confidence-weighted fusion in models/fusion.py, on a set of constructed conflict cases
— situations where text and face disagree, or where one modality is confident and the
other is flat/uncertain. Each case has a ground-truth label we assign by hand (these are
synthetic score distributions built to test specific fusion behavior, not real journal
entries, so "ground truth" here means "what a reasonable fusion policy should output").

Includes the user's real angry-face test result (face model: Happy 42% / Fearful 41% /
Angry 0%) as case #7, which motivated this whole comparison.
"""
import json

UNIFIED_EMOTIONS = ["angry", "disgusted", "fearful", "happy", "neutral", "sad", "surprised"]
TEXT_WEIGHT, FACE_WEIGHT = 0.55, 0.45


def naive_fuse(text_result, face_result):
    text_scores, face_scores = text_result["all_scores"], face_result["all_scores"]
    fused = {e: TEXT_WEIGHT * text_scores.get(e, 0.0) + FACE_WEIGHT * face_scores.get(e, 0.0)
             for e in UNIFIED_EMOTIONS}
    top = max(fused, key=fused.get)
    return top, fused[top]


def confidence_weighted_fuse(text_result, face_result):
    text_scores, face_scores = text_result["all_scores"], face_result["all_scores"]
    text_w_raw = TEXT_WEIGHT * text_result["confidence"]
    face_w_raw = FACE_WEIGHT * face_result["confidence"]
    total = text_w_raw + face_w_raw
    text_w, face_w = (text_w_raw / total, face_w_raw / total) if total > 0 else (TEXT_WEIGHT, FACE_WEIGHT)
    fused = {e: text_w * text_scores.get(e, 0.0) + face_w * face_scores.get(e, 0.0) for e in UNIFIED_EMOTIONS}
    top = max(fused, key=fused.get)
    return top, fused[top]


def flat(top_emotion, top_score, n=7):
    """A distribution peaked on top_emotion, rest split evenly."""
    rest = (1 - top_score) / (n - 1)
    return {e: (top_score if e == top_emotion else rest) for e in UNIFIED_EMOTIONS}


def result(emotion, score, all_scores=None):
    return {"dominant_emotion": emotion, "confidence": score,
            "all_scores": all_scores or flat(emotion, score), "emotion": emotion}


CASES = [
    # (name, text_result, face_result, expected)
    ("both confident, agree",
     result("happy", 0.95), result("happy", 0.92), "happy"),

    ("both confident, disagree (text should win — text is the more reliable modality per benchmark)",
     result("sad", 0.9), result("happy", 0.88), "sad"),

    ("confident text, flat/uncertain face — face shouldn't drag the result off text",
     result("sad", 0.9), result("happy", 0.30), "sad"),

    ("flat/uncertain text, confident face — face should be allowed to dominate here",
     result("neutral", 0.25), result("fearful", 0.9), "fearful"),

    ("both flat/uncertain — should land near neutral/low-confidence, not commit hard",
     result("angry", 0.30), result("sad", 0.28), None),  # None = "should NOT be confidently wrong"

    ("mild disagreement, both moderate confidence",
     result("surprised", 0.6), result("happy", 0.55), "surprised"),

    ("real case: user's exaggerated-angry face test — face gave Happy 42% / Fearful 41% / Angry 0%",
     result("neutral", 0.5),
     {"dominant_emotion": "happy", "confidence": 0.42, "emotion": "happy",
      "all_scores": {"happy": 0.42, "fearful": 0.41, "sad": 0.07, "neutral": 0.06,
                      "surprised": 0.05, "angry": 0.0, "disgusted": 0.0}},
     "angry"),  # ground truth: user was actually making an angry face
]


def main():
    rows = []
    naive_correct = weighted_correct = 0
    scoreable = 0
    for name, text_r, face_r, expected in CASES:
        naive_top, naive_conf = naive_fuse(text_r, face_r)
        weighted_top, weighted_conf = confidence_weighted_fuse(text_r, face_r)
        row = {
            "case": name,
            "expected": expected,
            "naive": {"emotion": naive_top, "confidence": round(naive_conf, 3)},
            "confidence_weighted": {"emotion": weighted_top, "confidence": round(weighted_conf, 3)},
        }
        if expected is not None:
            scoreable += 1
            naive_correct += naive_top == expected
            weighted_correct += weighted_top == expected
        rows.append(row)

    print(f"{'CASE':<90}{'NAIVE':<20}{'WEIGHTED':<20}{'EXPECTED':<12}")
    for r in rows:
        print(f"{r['case'][:88]:<90}"
              f"{r['naive']['emotion']+' '+str(round(r['naive']['confidence']*100))+'%':<20}"
              f"{r['confidence_weighted']['emotion']+' '+str(round(r['confidence_weighted']['confidence']*100))+'%':<20}"
              f"{str(r['expected']):<12}")

    print(f"\nScoreable cases: {scoreable}")
    print(f"Naive fusion correct:              {naive_correct}/{scoreable} = {naive_correct/scoreable*100:.0f}%")
    print(f"Confidence-weighted fusion correct: {weighted_correct}/{scoreable} = {weighted_correct/scoreable*100:.0f}%")

    with open("results/fusion_comparison.json", "w") as f:
        json.dump(rows, f, indent=2)
    print("\nSaved to results/fusion_comparison.json")


if __name__ == "__main__":
    main()
