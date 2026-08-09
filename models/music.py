"""Mood-arc soundtrack: turn a journal entry's emotional trajectory into a track sequence.

WHY AN ARC RATHER THAN A LOOKUP
-------------------------------
The obvious design is emotion -> playlist. It is also the harmful one. Handing sad music
to someone who is ruminating can entrench the state, and handing them cheerful music reads
as dismissal — the app talking over them rather than listening.

Music therapy's answer is the ISO-PRINCIPLE: meet the listener where they are, then move
gradually toward the target state. Never jump. This module implements that as three stages:

    MEET    matches the entry's opening emotion      "this understood me"
    BRIDGE  halfway between meet and lift            movement without whiplash
    LIFT    a gentler target state                   regulation

The input is `emotion_arc` — the per-sentence classification the text service already
produces for the UI. That is the part nothing else has: most apps know only the entry's
final label, so they can only pick a destination. Knowing the trajectory means an entry
that runs anxious -> resolved can be scored as anxious -> resolved.

TWO RULES THAT ARE NOT NEGOTIABLE
---------------------------------
1. Crisis suppresses everything. If crisis assessment flags an entry, this returns no
   tracks at all. Someone in crisis needs a helpline, not a playlist, and quietly
   recommending media there would be indefensible.
2. Anger calms before it lifts. The naive mapping raises valence first, which means
   answering an angry entry with upbeat music. The arc drops ENERGY first and only then
   moves valence — see ANGER_PATH below.

Valence/energy are on 0..1, following the convention popularised by Spotify's audio
features: valence is negative..positive affect, energy is calm..intense.
"""
from __future__ import annotations

# Where each emotion sits in the valence/energy plane. These are the "meet" targets —
# the music that matches how the entry opens.
EMOTION_VE = {
    "angry":     (0.30, 0.80),
    "disgusted": (0.30, 0.55),
    "fearful":   (0.30, 0.60),
    "happy":     (0.80, 0.70),
    "neutral":   (0.50, 0.50),
    "sad":       (0.20, 0.30),
    "surprised": (0.65, 0.70),
}

# Where the arc should end up for each starting emotion. Deliberately NOT (1.0, 1.0):
# the goal is regulation, not forced cheerfulness. Someone who wrote something sad should
# finish somewhere calmer and a little warmer, not somewhere euphoric.
LIFT_TARGET = {
    "angry":     (0.55, 0.35),   # calm first — see ANGER_PATH
    "disgusted": (0.55, 0.45),
    "fearful":   (0.55, 0.35),   # grounding: steady, low-arousal
    "happy":     (0.80, 0.65),   # already fine; sustain rather than escalate
    "neutral":   (0.60, 0.55),
    "sad":       (0.50, 0.40),   # lift valence, keep energy low — no forced jollity
    "surprised": (0.65, 0.55),
}

# Anger is the one emotion where the midpoint is wrong. Interpolating straight from
# (0.30, 0.80) to (0.55, 0.35) passes through moderate-valence/moderate-energy, which in
# practice means mid-tempo pop at someone who is furious. Instead the bridge drops energy
# while holding valence low, so the sequence is: loud and angry -> quiet and angry ->
# quiet and steadier. Calm down before you cheer up.
ANGER_PATH = (0.32, 0.45)

# Jamendo has no valence field, so each stage is resolved to its tags. Ordered roughly
# from low to high on each axis; the resolver picks by nearest bucket.
VALENCE_TAGS = [
    (0.25, ["melancholy", "sad", "dark"]),
    (0.45, ["introspective", "pensive", "ambient"]),
    (0.65, ["calm", "hopeful", "warm"]),
    (1.01, ["happy", "uplifting", "positive"]),
]
# Energy tags are split by valence, because "intense" and "upbeat" are different axes
# and collapsing them is how you end up answering an angry entry with cheerful music.
# High energy at LOW valence is heavy/driving; high energy at HIGH valence is upbeat.
ENERGY_TAGS_NEGATIVE = [
    (0.35, ["slow", "quiet", "melancholic"]),
    (0.60, ["brooding", "moody", "atmospheric"]),
    (1.01, ["intense", "powerful", "driving"]),
]
ENERGY_TAGS_POSITIVE = [
    (0.35, ["calm", "gentle", "relaxing"]),
    (0.60, ["chill", "mellow", "acoustic"]),
    (1.01, ["upbeat", "energetic", "lively"]),
]
VALENCE_SPLIT = 0.50

STAGES = ("meet", "bridge", "lift")


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, v))


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _tags_for(valence: float, energy: float, stage_index: int = 0) -> list[str]:
    """One tag from each axis — querying all six at once reliably returns nothing.

    `stage_index` picks WHICH synonym from each bucket. Without it, arcs that move only
    a little (happy runs 0.80/0.70 -> 0.80/0.65) put all three stages in the same bucket
    and emit three identical queries, which is not an arc at all — the user hears the
    same mood three times. Since the words in a bucket are near-synonyms, varying by
    stage keeps the mood while making the queries genuinely different, so each stage
    surfaces different tracks.
    """
    v = next(tags for hi, tags in VALENCE_TAGS if valence < hi)
    energy_scale = (ENERGY_TAGS_POSITIVE if valence >= VALENCE_SPLIT
                    else ENERGY_TAGS_NEGATIVE)
    e = next(tags for hi, tags in energy_scale if energy < hi)
    i = stage_index % len(v)
    return [v[i], e[stage_index % len(e)]]


def dominant_opening(emotion_arc: list, fallback: str = "neutral") -> str:
    """The emotion the entry OPENS on, which is what the arc should meet.

    Deliberately not the entry's overall label. Someone who writes three anxious
    sentences and one calm one at the end has had an anxious experience; meeting them at
    'calm' would skip the part that mattered. Uses the first half of the arc, weighted by
    the classifier's confidence.
    """
    if not emotion_arc:
        return fallback
    head = emotion_arc[: max(1, len(emotion_arc) // 2)]
    scores: dict[str, float] = {}
    for step in head:
        emo = step.get("emotion")
        if emo in EMOTION_VE:
            scores[emo] = scores.get(emo, 0.0) + float(step.get("confidence") or 0.0)
    return max(scores, key=scores.get) if scores else fallback


def build_arc(emotion_arc: list, overall_emotion: str = "neutral") -> list[dict]:
    """Three (valence, energy) waypoints implementing the iso-principle."""
    start = dominant_opening(emotion_arc, fallback=overall_emotion)
    v0, e0 = EMOTION_VE.get(start, EMOTION_VE["neutral"])
    v2, e2 = LIFT_TARGET.get(start, LIFT_TARGET["neutral"])
    v1, e1 = ANGER_PATH if start == "angry" else (_lerp(v0, v2, 0.5), _lerp(e0, e2, 0.5))

    points = [(v0, e0), (v1, e1), (v2, e2)]
    return [
        {
            "stage": stage,
            "valence": round(_clamp(v), 3),
            "energy": round(_clamp(e), 3),
            "tags": _tags_for(_clamp(v), _clamp(e), i),
            "from_emotion": start,
        }
        for i, (stage, (v, e)) in enumerate(zip(STAGES, points))
    ]


def build_week_arc(emotion_counts: dict) -> list[dict]:
    """Feature 2: same engine, fed a week of dominant emotions instead of one entry.

    The week's most-felt emotion becomes the meet point, so the weekly soundtrack opens
    where the week actually sat rather than where it happened to end.
    """
    if not emotion_counts:
        return build_arc([], "neutral")
    top = max(emotion_counts, key=lambda k: emotion_counts[k])
    synthetic = [{"emotion": top, "confidence": 1.0}]
    return build_arc(synthetic, overall_emotion=top)


def is_suppressed(crisis: dict | None) -> bool:
    """Crisis entries get no soundtrack. See the module docstring."""
    return bool(crisis and crisis.get("is_crisis"))
