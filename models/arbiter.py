import os

from groq import AsyncGroq
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

UNIFIED_EMOTIONS = ["angry", "disgusted", "fearful", "happy", "neutral", "sad", "surprised"]

# Cheap/fast model — this is a one-word classification decision, not response generation,
# so it doesn't need the 70B model's depth. Keeps the added latency/cost on the minority
# of genuinely ambiguous cases small.
ARBITER_MODEL = "llama-3.1-8b-instant"

SYSTEM_PROMPT = """You resolve disagreements between two automated emotion readings of the
same message: a text-sentiment classifier and a facial-expression classifier. They read
different emotions with comparable confidence, so neither can be trusted blindly. Read the
person's actual words and decide which single emotion most likely reflects what they're
really feeling — accounting for things simple classifiers miss, like sarcasm, tone, and
context. Respond with exactly one word from this list, nothing else: angry, disgusted,
fearful, happy, neutral, sad, surprised."""


class Arbiter:
    def __init__(self):
        self.client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

    def should_arbitrate(self, fusion_result: dict) -> bool:
        """Only fires on genuine unresolved conflict — both modalities disagree, neither
        is neutral, and neither dominates on confidence. Fusion already resolves the easier
        cases (agreement, one modality clearly stronger, one modality reading neutral)
        without needing an extra LLM call on every single message."""
        return fusion_result.get("resolution_reason", "").startswith("conflict_resolved_to_")

    async def arbitrate(self, text: str, text_result: dict, face_result: dict, fusion_result: dict) -> dict:
        if not self.should_arbitrate(fusion_result):
            return fusion_result

        user_prompt = f"""Message: \"\"\"{text[:500]}\"\"\"
Text-sentiment model reading: {text_result['dominant_emotion']} ({text_result['confidence']:.0%} confidence)
Facial-expression model reading: {face_result['emotion']} ({face_result['confidence']:.0%} confidence)

Which single emotion is most likely correct?"""

        try:
            completion = await self.client.chat.completions.create(
                model=ARBITER_MODEL,
                messages=[{"role": "system", "content": SYSTEM_PROMPT},
                          {"role": "user", "content": user_prompt}],
                max_tokens=10,
                temperature=0.2,
            )
            answer = (completion.choices[0].message.content or "").strip().lower()
            answer = "".join(c for c in answer if c.isalpha())
        except Exception as e:
            print(f"[Arbiter] ERROR: {type(e).__name__}: {e} — keeping numeric fusion result")
            return fusion_result

        if answer not in UNIFIED_EMOTIONS:
            print(f"[Arbiter] Unparseable response {answer!r} — keeping numeric fusion result")
            return fusion_result

        if answer == fusion_result["unified_emotion"]:
            return fusion_result

        print(f"[Arbiter] Overrode {fusion_result['unified_emotion']!r} -> {answer!r} for: {text[:60]!r}")
        # Rewrite all_scores too, not just the label — otherwise the XAI breakdown would
        # still show the old (overridden) emotion's bar as the tallest while the headline
        # says something else, undermining the explainability the app is built around.
        ARBITER_CONFIDENCE = 0.6
        rest = (1 - ARBITER_CONFIDENCE) / (len(UNIFIED_EMOTIONS) - 1)
        adjusted_scores = {e: (ARBITER_CONFIDENCE if e == answer else rest) for e in UNIFIED_EMOTIONS}
        return {
            **fusion_result,
            "unified_emotion": answer,
            "unified_confidence": ARBITER_CONFIDENCE,
            "all_scores": adjusted_scores,
            "resolution_reason": "llm_arbitration",
            "pre_arbitration_emotion": fusion_result["unified_emotion"],
        }
