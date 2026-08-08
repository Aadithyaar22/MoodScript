import os
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

EMOTION_MODEL = os.getenv("MOODSCRIPT_EMOTION_MODEL",
                          "j-hartmann/emotion-english-distilroberta-base")

# The overall label now comes from classifying the WHOLE entry in one pass.
# Measured on 1,056 held-out journal-style texts, splitting into sentences and
# recombining them with the position/length/confidence weighting cost 3.7 points
# against simply classifying the entry (60.80% vs 64.49%, p=2.4e-05): these
# entries average ~22 words, so splitting destroys the context the classifier
# needs and then reweights the fragments with hand-chosen coefficients that were
# never fitted. Per-sentence classification is still run, because the emotion arc
# shown in the UI genuinely needs it — it just no longer decides the headline label.
# Set MOODSCRIPT_SENTENCE_AGGREGATE=1 to restore the previous behaviour.
USE_SENTENCE_AGGREGATE = os.getenv("MOODSCRIPT_SENTENCE_AGGREGATE", "").lower() in ("1", "true", "yes")


class TextEmotionModel:
    def __init__(self):
        print("Loading spaCy...")
        self.nlp = spacy.load("en_core_web_sm")

        # roberta-large scores 67.33% on the journal benchmark against 64.49% here,
        # but peaks at 1.82GB resident against this service's 2Gi Cloud Run cap —
        # too little headroom to run safely. Staying on the distilled base; revisit
        # if the memory limit is ever raised.
        print(f"Loading emotion model {EMOTION_MODEL}...")
        self.emotion_classifier = pipeline(
            "text-classification",
            model=EMOTION_MODEL,
            top_k=None,
            device=-1,
        )

        if os.getenv("ENABLE_CLINICAL_TONE", "true").lower() == "true":
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
        else:
            print("Clinical tone model disabled (ENABLE_CLINICAL_TONE=false) — skipping to save memory.")
            self.clinical_classifier = None

        print("Text models ready.")

    def _classify_sentence(self, sentence: str):
        if not sentence.strip():
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

    # --- retired heuristics, retained only so research/eval_text_pipeline_ablation.py
    # --- can still reproduce the ablation reported in the paper. Nothing in the
    # --- serving path calls these.
    #
    # The idea was that the classifier reads emotion words at face value regardless of
    # negation ('not scared' still scores high on fear), so dampening toward neutral
    # beats a confidently wrong flip. It validated on 49 hand-written cases (72% -> 78%)
    # and did not survive contact with real data: across 1,056 held-out journal texts it
    # changed 32 labels, broke 20 correct answers and fixed none, costing 1.89 points.

    def _dampen_for_negation(self, conf_dict: dict) -> dict:
        top_emotion = max(conf_dict, key=conf_dict.get)
        if top_emotion == "neutral":
            return conf_dict
        damped = {e: v * 0.5 for e, v in conf_dict.items()}
        damped["neutral"] = damped.get("neutral", 0.0) + conf_dict[top_emotion] * 0.5
        total = sum(damped.values())
        return {e: v / total for e, v in damped.items()} if total else damped

    def _has_negation(self, sent) -> bool:
        """Only flags true predicate-adjective negation ('not happy', "isn't scared") —
        deliberately narrower than 'any neg token', since idiomatic negated verbs like
        "can't stop crying", "can't believe", "won't listen" are extremely common in
        emotional text and don't actually invert the sentence's meaning."""
        for tok in sent:
            if tok.dep_ == "neg" and tok.head.pos_ == "AUX":
                if any(child.pos_ == "ADJ" and child.dep_ == "acomp" for child in tok.head.children):
                    return True
        return False

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
        sents = [s for s in doc.sents if s.text.strip()]
        sentences = [s.text.strip() for s in sents]

        # Per-sentence pass drives the emotion arc shown in the UI.
        sentence_results = []
        for sent in sents:
            r = self._classify_sentence(sent.text.strip())
            if r:
                sentence_results.append((sent.text.strip(), r))
        emotion_arc = [
            {"sentence": sent[:80], "emotion": r["emotion"], "confidence": round(r["confidence"], 3)}
            for sent, r in sentence_results
        ]

        # Headline label: classify the entry whole, keeping its context intact.
        if USE_SENTENCE_AGGREGATE:
            agg = self._weighted_aggregate(sentence_results)
        else:
            whole = self._classify_sentence(text.strip())
            if whole:
                agg = {"dominant_emotion": whole["emotion"],
                       "confidence": whole["confidence"],
                       "all_scores": whole["all_scores"]}
            else:
                # empty or unclassifiable input — fall back rather than fail
                agg = self._weighted_aggregate(sentence_results)

        return {
            "dominant_emotion": agg["dominant_emotion"],
            "confidence": agg["confidence"],
            "all_scores": agg["all_scores"],
            "emotion_arc": emotion_arc,
            "clinical_tone": self._clinical_tone(text),
            "sentence_count": len(sentences),
        }
