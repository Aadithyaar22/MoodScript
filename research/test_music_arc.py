"""Checks on the mood-arc engine. No API, no network — pure logic.

These assert the properties that make the feature safe and non-obvious, not just that
the code runs: that anger calms before it cheers, that the arc opens where the entry
opened rather than where it ended, and that a crisis entry produces nothing at all.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from models.music import (EMOTION_VE, build_arc, build_week_arc,  # noqa: E402
                          dominant_opening, is_suppressed)

fails = []


def check(name, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}{'  ' + detail if detail else ''}")
    if not cond:
        fails.append(name)


print("\n1. anger calms BEFORE it lifts (the whole point of ANGER_PATH)")
arc = build_arc([{"emotion": "angry", "confidence": 0.9}])
meet, bridge, lift = arc
check("energy falls from meet to bridge",
      bridge["energy"] < meet["energy"],
      f"{meet['energy']} -> {bridge['energy']}")
check("valence does NOT rise much at the bridge",
      bridge["valence"] - meet["valence"] < 0.10,
      f"{meet['valence']} -> {bridge['valence']}")
check("bridge is calmer than a naive midpoint would be",
      bridge["energy"] < (meet["energy"] + lift["energy"]) / 2 + 1e-9,
      f"bridge {bridge['energy']} vs naive {(meet['energy']+lift['energy'])/2:.3f}")
# Meeting anger with INTENSE music is correct and is the point of the iso-principle.
# Meeting it with CHEERFUL music is the failure mode. Those are different axes, so the
# assertion bans positive-affect tags rather than high-energy ones.
CHEERFUL = ("upbeat", "happy", "uplifting", "positive", "lively")
check("no cheerful tag anywhere in an angry arc",
      not any(t in CHEERFUL for s in arc for t in s["tags"]),
      str([s["tags"] for s in arc]))
check("the meet stage IS allowed to be intense",
      any(t in ("intense", "powerful", "driving") for t in arc[0]["tags"]),
      str(arc[0]["tags"]))

print("\n2. the arc MEETS where the entry opened, not where it ended")
anxious_to_calm = [
    {"emotion": "fearful", "confidence": 0.9},
    {"emotion": "fearful", "confidence": 0.8},
    {"emotion": "neutral", "confidence": 0.7},
    {"emotion": "happy",   "confidence": 0.6},
]
check("opens on fearful despite ending happy",
      dominant_opening(anxious_to_calm) == "fearful",
      dominant_opening(anxious_to_calm))

print("\n3. sadness lifts valence without forcing energy up")
sad = build_arc([{"emotion": "sad", "confidence": 0.95}])
check("valence rises", sad[2]["valence"] > sad[0]["valence"],
      f"{sad[0]['valence']} -> {sad[2]['valence']}")
check("energy stays low (<= 0.5)", sad[2]["energy"] <= 0.5, str(sad[2]["energy"]))

print("\n4. happiness is sustained, not escalated")
happy = build_arc([{"emotion": "happy", "confidence": 0.9}])
check("does not push valence past its meet point",
      happy[2]["valence"] <= happy[0]["valence"] + 1e-9,
      f"{happy[0]['valence']} -> {happy[2]['valence']}")

print("\n5. crisis suppresses the feature entirely")
check("is_crisis True  -> suppressed", is_suppressed({"is_crisis": True, "reason": "x"}))
check("is_crisis False -> allowed", not is_suppressed({"is_crisis": False}))
check("None            -> allowed", not is_suppressed(None))

print("\n6. every emotion produces a well-formed 3-stage arc")
for emo in EMOTION_VE:
    a = build_arc([{"emotion": emo, "confidence": 1.0}])
    ok = (len(a) == 3
          and [s["stage"] for s in a] == ["meet", "bridge", "lift"]
          and all(0.0 <= s["valence"] <= 1.0 and 0.0 <= s["energy"] <= 1.0 for s in a)
          and all(len(s["tags"]) == 2 for s in a))
    check(f"{emo:<10} well-formed", ok, str([(s['valence'], s['energy']) for s in a]))

print("\n7. degenerate inputs do not raise")
for label, val in (("empty arc", []), ("unknown emotion",
                   [{"emotion": "bored", "confidence": 0.5}]),
                   ("missing confidence", [{"emotion": "sad"}])):
    try:
        a = build_arc(val)
        check(f"{label:<18} -> {len(a)} stages", len(a) == 3)
    except Exception as e:
        check(f"{label} does not raise", False, f"{type(e).__name__}: {e}")

print("\n8. weekly arc opens on the week's most-felt emotion")
wk = build_week_arc({"sad": 5, "happy": 2, "neutral": 1})
check("week of mostly sadness meets at sad", wk[0]["from_emotion"] == "sad",
      wk[0]["from_emotion"])
check("empty week does not raise", len(build_week_arc({})) == 3)

print(f"\n{'ALL CHECKS PASSED' if not fails else f'{len(fails)} FAILED: {fails}'}")
sys.exit(1 if fails else 0)
