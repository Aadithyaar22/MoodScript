import numpy as np
from lime.lime_text import LimeTextExplainer

UNIFIED_EMOTIONS = ["angry", "disgusted", "fearful", "happy", "neutral", "sad", "surprised"]
JHARTMANN_TO_UNIFIED = {
    "anger": "angry", "disgust": "disgusted", "fear": "fearful",
    "joy": "happy", "neutral": "neutral", "sadness": "sad", "surprise": "surprised",
}

class XAIExplainer:
    def __init__(self, text_model):
        self.text_model = text_model
        self.explainer = LimeTextExplainer(class_names=UNIFIED_EMOTIONS)

    def _predict_proba(self, texts: list) -> np.ndarray:
        results = []
        for text in texts:
            try:
                preds = self.text_model.emotion_classifier(text[:512])
                if preds and isinstance(preds[0], list):
                    preds = preds[0]
                scores = [0.0] * len(UNIFIED_EMOTIONS)
                for p in preds:
                    unified = JHARTMANN_TO_UNIFIED.get(p["label"].lower(), p["label"].lower())
                    if unified in UNIFIED_EMOTIONS:
                        scores[UNIFIED_EMOTIONS.index(unified)] = p["score"]
                results.append(scores)
            except Exception:
                results.append([1/7] * len(UNIFIED_EMOTIONS))
        return np.array(results)

    def explain(self, text: str, text_result: dict) -> dict:
        # Use full text sentences, not the truncated arc snippets
        import spacy
        nlp = self.text_model.nlp
        doc = nlp(text)
        sentences = [s.text.strip() for s in doc.sents if s.text.strip()]

        # Find highest confidence sentence using arc as index guide
        arc = text_result.get("emotion_arc", [])
        if arc and sentences:
            best_idx = max(range(len(arc)), key=lambda i: arc[i]["confidence"])
            key_sentence = sentences[best_idx] if best_idx < len(sentences) else sentences[0]
        else:
            key_sentence = sentences[0] if sentences else text[:200]

        top_words = []
        try:
            dominant = text_result["dominant_emotion"]
            label_idx = UNIFIED_EMOTIONS.index(dominant) if dominant in UNIFIED_EMOTIONS else 4
            exp = self.explainer.explain_instance(
                key_sentence, self._predict_proba,
                num_features=6, labels=[label_idx], num_samples=80,
            )
            top_words = [
                {"word": w, "weight": round(float(s), 4), "direction": "positive" if s > 0 else "negative"}
                for w, s in exp.as_list(label=label_idx)[:6]
            ]
        except Exception as e:
            print(f"LIME error (non-fatal): {e}")
            top_words = [{"word": w, "weight": 0.1, "direction": "positive"} for w in key_sentence.split()[:6]]

        return {
            "key_sentence": key_sentence,
            "top_words": top_words,
            "text_confidence_array": text_result.get("all_scores", {}),
        }
