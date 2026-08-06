"""Validates the LLM arbiter (models/arbiter.py) against constructed conflict cases —
including a sarcasm case, since that's the specific failure mode nothing else in this
project fixed (text classifier alone: 0/2 on sarcasm every time it was tested)."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from models.arbiter import Arbiter  # noqa: E402
from models.fusion import FusionLayer  # noqa: E402


def flat(top_emotion, top_score, n=7):
    emotions = ["angry", "disgusted", "fearful", "happy", "neutral", "sad", "surprised"]
    rest = (1 - top_score) / (n - 1)
    return {e: (top_score if e == top_emotion else rest) for e in emotions}


def text_result(emotion, conf):
    return {"dominant_emotion": emotion, "confidence": conf, "all_scores": flat(emotion, conf)}


def face_result(emotion, conf):
    return {"emotion": emotion, "confidence": conf, "all_scores": flat(emotion, conf)}


CASES = [
    ("Oh great, another Monday, I'm just thrilled.",
     text_result("happy", 0.6), face_result("angry", 0.55), "angry",
     "sarcasm — text classifier reads 'thrilled' literally, face shows real anger"),

    ("I can't believe you remembered my favorite song after all these years.",
     text_result("surprised", 0.55), face_result("happy", 0.5), "happy",
     "genuine mixed surprise+happy — either is defensible, checking it doesn't crash/misfire wildly"),

    ("Nothing happened today, just a normal Tuesday.",
     text_result("sad", 0.5), face_result("neutral", 0.45), "neutral",
     "text over-reads mundane text as sad; face + content should win toward neutral"),
]


async def main():
    fusion = FusionLayer()
    arbiter = Arbiter()
    for text, tr, fr, expected, note in CASES:
        fusion_result = fusion.fuse(tr, fr)
        print(f"\n{'='*80}\n{text}\n({note})")
        print(f"  text={tr['dominant_emotion']}({tr['confidence']:.0%})  face={fr['emotion']}({fr['confidence']:.0%})")
        print(f"  numeric fusion -> {fusion_result['unified_emotion']} (reason={fusion_result['resolution_reason']})")
        result = await arbiter.arbitrate(text, tr, fr, fusion_result)
        changed = result["unified_emotion"] != fusion_result["unified_emotion"]
        print(f"  after arbiter  -> {result['unified_emotion']} "
              f"{'(CHANGED)' if changed else '(unchanged)'} — expected: {expected}")


if __name__ == "__main__":
    asyncio.run(main())
