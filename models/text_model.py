import spacy
from transformers import pipeline
from collections import defaultdict

JHARTMANN_TO_UNIFIED = {
    "anger": "angry", "disgust": "disgusted", "fear": "fearful",
    "joy": "happy", "neutral": "neutral", "sadness": "sad", "surprise": "surprised",
}
UNIFIED_EMOTIONS = ["angry", "disgusted", "fearful", "happy", "neutral", "sad", "surprised"]

# GoEmotions → clinical tone mapping
GOEMOTION_TO_TONE = {
    "grief": "depression", "sadness": "depression", "remorse": "depression",
    "nervousness": "anxiety", "fear": "anxiety", "worry": "anxiety",
    "anger": "stress", "annoyance": "stress", "frustration": "stress",
    "joy": "positive", "excitement": "positive", "gratitude": "positive",
    "confusion": "confusion", "curiosity": "curiosity",
}

class TextEmotionModel:
    def __init__(self):
        print("Loading spaCy...")
        self.nlp = spacy.load("en_core_web_sm")

        print("Loading j-hartmann emotion model...")
        self.emotion_classifier = pipeline(
            "text-classification",
            model="j-hartmann/emotion-english-distilroberta-base",
            top_k=None,
            device=-1,
        )

        print("Loading GoEmotions clinical tone model...")
        try:
            self.clinical_classifier = pipeline(
                "text-classification",
                model="SamLowe/roberta-base-go_emotions",
                top_k=3,
                device=-1,
            )
            print("Clinical tone model ready.")
        except Exception as e:
            print(f"Clinical tone model skipped: {e}")
            self.clinical_classifier = None

        print("Text models ready.")

    def _classify_sentence(self, sentence: str):
        if len(sentence.split()) < 3:
            return None
        try:
            preds = self.emotion_classifier(sentence[:512])
            if preds and isinstance(preds[0], list):
                preds = preds[0]
            conf_dict = {}
            for p in preds:
                unified = JHARTMANN_TO_UNIFIED.get(p["label"].lower(), p["label"].lower())
                conf_dict[unified] = p["score"]
            for e in UNIFIED_EMOTIONS:
                if e not in conf_dict:
                    conf_dict[e] = 0.0
            top = max(conf_dict, key=conf_dict.get)
            return {"emotion": top, "confidence": conf_dict[top], "all_scores": conf_dict}
        except Exception as e:
            print(f"Sentence classify error: {e}")
            return None

    def _weighted_aggregate(self, sentence_results: list) -> dict:
        n = len(sentence_results)
        if n == 0:
            return {"dominant_emotion": "neutral", "confidence": 0.5,
                    "all_scores": {e: 1/7 for e in UNIFIED_EMOTIONS}}
        emotion_scores = defaultdict(float)
        total_weight = 0.0
        for i, (sent_text, result) in enumerate(sentence_results):
            position_weight = (i + 1) / n
            length_weight = min(len(sent_text.split()) / 20, 1.5)
            conf_weight = result["confidence"]
            weight = position_weight * 0.4 + length_weight * 0.3 + conf_weight * 0.3
            for emotion, score in result["all_scores"].items():
                emotion_scores[emotion] += score * weight
            total_weight += weight
        if total_weight > 0:
            emotion_scores = {k: v / total_weight for k, v in emotion_scores.items()}
        for e in UNIFIED_EMOTIONS:
            if e not in emotion_scores:
                emotion_scores[e] = 0.0
        dominant = max(emotion_scores, key=emotion_scores.get)
        return {"dominant_emotion": dominant, "confidence": float(emotion_scores[dominant]),
                "all_scores": {k: float(v) for k, v in emotion_scores.items()}}

    def _clinical_tone(self, text: str):
        if not self.clinical_classifier:
            return None
        try:
            results = self.clinical_classifier(text[:512])
            if results and isinstance(results[0], list):
                results = results[0]
            top_label = results[0].get("label", "").lower()
            return GOEMOTION_TO_TONE.get(top_label, top_label)
        except Exception:
            return None

    def predict(self, text: str) -> dict:
        doc = self.nlp(text)
        sentences = [s.text.strip() for s in doc.sents if s.text.strip()]
        sentence_results = []
        for sent in sentences:
            r = self._classify_sentence(sent)
            if r:
                sentence_results.append((sent, r))
        agg = self._weighted_aggregate(sentence_results)
        emotion_arc = [
            {"sentence": sent[:80], "emotion": r["emotion"], "confidence": round(r["confidence"], 3)}
            for sent, r in sentence_results
        ]
        return {
            "dominant_emotion": agg["dominant_emotion"],
            "confidence": agg["confidence"],
            "all_scores": agg["all_scores"],
            "emotion_arc": emotion_arc,
            "clinical_tone": self._clinical_tone(text),
            "sentence_count": len(sentences),
        }
