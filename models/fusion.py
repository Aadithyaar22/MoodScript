"""Multimodal fusion of the text and face emotion signals.

METHOD — calibration-aware log-linear fusion
--------------------------------------------
The previous rule was a confidence-weighted linear average: each modality's fixed
prior scaled by its own top-class probability, then blended additively. Two
measured problems with that (see research/ for the full evaluation):

1. The two confidences were not on the same scale. Measured on a held-out paired
   benchmark, the text model's expected calibration error was 0.217 (it claimed
   0.66 confidence while being correct 0.44 of the time) against 0.015 for the
   face model. Multiplying a prior by raw confidence therefore over-trusted the
   worse-calibrated modality, and the linear rule scored *below* using the face
   modality alone (85.83% vs 88.69%).

2. A weighted average cannot veto. If one modality assigns ~0 probability to a
   class, the other can still carry it, because a sum is dominated by its larger
   term. Under conditional independence of the modalities given the label, the
   product is the Bayesian combination; the sum is not.

So each modality is now temperature-calibrated onto a common scale, weighted by a
class-conditional reliability estimate rather than one scalar, and combined by
log-linear (product-of-experts) pooling.

Measured on held-out test splits of two independent paired benchmarks, by running
THIS module (research/verify_production_fusion.py) — not a research reimplementation,
and using the frozen pooled constants below rather than per-set fitted ones:

    strategy                          set A     set B
    text only                         49.74     64.57
    face only                         88.39     88.69
    linear + confidence (previous)    83.36     85.83
    this method                       91.51     92.83

Significant against both the previous rule and the stronger single modality
(p = 4.8e-8 and p = 5.2e-4 on set A; p = 9.1e-15 and p = 7.7e-9 on set B).

Set B now includes 400 neutral pairs (DailyDialog "no emotion" text + FER2013
neutral faces), added because the EmpatheticDialogues source has no neutral
category and its absence was inflating every number measured on it. Including the
class both modalities are worst at cost 0.35 points of accuracy and raised macro-F1
from 80.66 to 93.39 — the old macro-F1 was dragged down by neutral scoring zero by
construction.

Beating face-only is the result that matters: the face model is the stronger
modality, so a fusion rule that cannot outperform it is not earning its complexity.

Set MOODSCRIPT_LEGACY_FUSION=1 to fall back to the previous linear rule.
"""
import math
import os

UNIFIED_EMOTIONS = ["angry", "disgusted", "fearful", "happy", "neutral", "sad", "surprised"]
TEXT_WEIGHT = 0.55
FACE_WEIGHT = 0.45
_EPS = 1e-12

# Fitted by minimising NLL on the pooled calibration splits of both paired
# benchmarks (n=1831). Both sets are pooled so every class has real support from
# more than one text domain.
# Reproduce: research/fit_fusion_constants.py (which refuses to emit a constant for
# any class with under 25 calibration examples — the guard exists because fitting on
# the journal set alone, before it had a neutral class, once produced a neutral
# reliability of 0.029 out of thin air).
TEXT_TEMPERATURE = 1.6990
FACE_TEMPERATURE = 0.9171

# Smoothed per-class precision of each modality on the class it predicts. Text
# reliability spans 0.36–0.71 across classes, which is why a single scalar weight
# per modality is not adequate.
#
# Neutral was previously estimated from 100 calibration examples, all of them
# GoEmotions Reddit comments, and came out at 0.2356 (text) / 0.6914 (face). With
# 300 examples including journal-domain neutral the true values are 0.5161 and
# 0.8674 — the old constants had production under-trusting neutral by roughly half
# on the text side. That is a correction to the model's behaviour, not just to a
# benchmark number.
TEXT_RELIABILITY = {
    "angry": 0.6784, "disgusted": 0.3556, "fearful": 0.7069, "happy": 0.6505,
    "neutral": 0.5161, "sad": 0.6594, "surprised": 0.5702,
}
FACE_RELIABILITY = {
    "angry": 0.9122, "disgusted": 0.9748, "fearful": 0.8443, "happy": 0.9323,
    "neutral": 0.8674, "sad": 0.8243, "surprised": 0.9558,
}

_LEGACY = os.getenv("MOODSCRIPT_LEGACY_FUSION", "").lower() in ("1", "true", "yes")


def _normalise(scores: dict) -> dict:
    total = sum(max(v, 0.0) for v in scores.values())
    if total <= 0:
        return {e: 1.0 / len(UNIFIED_EMOTIONS) for e in UNIFIED_EMOTIONS}
    return {e: max(scores.get(e, 0.0), 0.0) / total for e in UNIFIED_EMOTIONS}


def _temperature_scale(scores: dict, temperature: float) -> dict:
    """Soften or sharpen a distribution. T>1 makes an over-confident model humbler.
    Implemented on log-probabilities, which is equivalent to scaling the logits."""
    logits = {e: math.log(max(v, _EPS)) / temperature for e, v in scores.items()}
    top = max(logits.values())
    exp = {e: math.exp(v - top) for e, v in logits.items()}
    total = sum(exp.values()) or 1.0
    return {e: v / total for e, v in exp.items()}


class FusionLayer:
    def fuse(self, text_result: dict, face_result) -> dict:
        if face_result is None:
            return {
                "unified_emotion": text_result["dominant_emotion"],
                "unified_confidence": text_result["confidence"],
                "all_scores": text_result["all_scores"],
                "resolution_reason": "text_only",
                "modalities_used": ["text"],
                "text_weight": 1.0,
                "face_weight": 0.0,
            }

        text_scores = _normalise(text_result["all_scores"])
        face_scores = _normalise(face_result["all_scores"])

        if _LEGACY:
            fused, text_w, face_w = self._fuse_linear(
                text_scores, face_scores,
                text_result["confidence"], face_result["confidence"])
        else:
            fused, text_w, face_w = self._fuse_loglinear(text_scores, face_scores)

        unified_emotion = max(fused, key=fused.get)
        resolution_reason = self._resolve(
            text_result["dominant_emotion"], face_result["emotion"],
            text_result["confidence"], face_result["confidence"], unified_emotion,
        )
        return {
            "unified_emotion": unified_emotion,
            "unified_confidence": float(fused[unified_emotion]),
            "all_scores": {k: float(v) for k, v in fused.items()},
            "resolution_reason": resolution_reason,
            "modalities_used": ["text", "face"],
            "text_weight": float(text_w),
            "face_weight": float(face_w),
        }

    def _fuse_loglinear(self, text_scores, face_scores):
        """Calibrate, weight by class-conditional reliability, pool in log space."""
        t_cal = _temperature_scale(text_scores, TEXT_TEMPERATURE)
        f_cal = _temperature_scale(face_scores, FACE_TEMPERATURE)

        t_top = max(t_cal, key=t_cal.get)
        f_top = max(f_cal, key=f_cal.get)
        a_text = TEXT_WEIGHT * TEXT_RELIABILITY.get(t_top, 0.5) * t_cal[t_top]
        a_face = FACE_WEIGHT * FACE_RELIABILITY.get(f_top, 0.5) * f_cal[f_top]
        total = a_text + a_face
        if total <= 0:
            a_text, a_face = TEXT_WEIGHT, FACE_WEIGHT
        else:
            a_text, a_face = a_text / total, a_face / total

        log_fused = {
            e: a_text * math.log(max(t_cal[e], _EPS)) + a_face * math.log(max(f_cal[e], _EPS))
            for e in UNIFIED_EMOTIONS
        }
        top = max(log_fused.values())
        exp = {e: math.exp(v - top) for e, v in log_fused.items()}
        norm = sum(exp.values()) or 1.0
        return {e: v / norm for e, v in exp.items()}, a_text, a_face

    def _fuse_linear(self, text_scores, face_scores, text_conf, face_conf):
        """Previous behaviour, retained behind MOODSCRIPT_LEGACY_FUSION."""
        t_raw = TEXT_WEIGHT * text_conf
        f_raw = FACE_WEIGHT * face_conf
        total = t_raw + f_raw
        text_w, face_w = (t_raw / total, f_raw / total) if total > 0 else (TEXT_WEIGHT, FACE_WEIGHT)
        fused = {e: text_w * text_scores.get(e, 0.0) + face_w * face_scores.get(e, 0.0)
                 for e in UNIFIED_EMOTIONS}
        return fused, text_w, face_w

    def _resolve(self, text_em, face_em, text_conf, face_conf, final_em):
        if text_em == face_em:
            return "agreement"
        conf_gap = abs(text_conf - face_conf)
        if conf_gap > 0.25:
            return f"dominant_confidence_{'text' if text_conf > face_conf else 'face'}"
        if face_em == "neutral":
            return "text_override"
        if text_em == "neutral":
            return "face_override"
        return f"conflict_resolved_to_{final_em}"
