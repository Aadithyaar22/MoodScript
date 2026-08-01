UNIFIED_EMOTIONS = ["angry", "disgusted", "fearful", "happy", "neutral", "sad", "surprised"]
TEXT_WEIGHT = 0.55
FACE_WEIGHT = 0.45

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
        text_scores = text_result["all_scores"]
        face_scores = face_result["all_scores"]
        fused = {e: TEXT_WEIGHT * text_scores.get(e, 0.0) + FACE_WEIGHT * face_scores.get(e, 0.0)
                 for e in UNIFIED_EMOTIONS}
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
            "text_weight": TEXT_WEIGHT,
            "face_weight": FACE_WEIGHT,
        }

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
