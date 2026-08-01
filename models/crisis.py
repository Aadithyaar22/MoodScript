import re

_CRISIS_PATTERNS = [
    r"\bkill(ing)? myself\b",
    r"\bend(ing)? my life\b",
    r"\bwant(ed)? to die\b",
    r"\bwish i (was|were) dead\b",
    r"\bdon'?t want to (be alive|live anymore|exist)\b",
    r"\bsuicid\w*\b",
    r"\bself[\s-]?harm\w*\b",
    r"\bcutting myself\b",
    r"\bbetter off dead\b",
    r"\bno reason to live\b",
    r"\bno point (in )?(living|going on)\b",
]
_CRISIS_RE = re.compile("|".join(_CRISIS_PATTERNS), re.IGNORECASE)

_NEGATIVE_EMOTIONS = {"sad", "fearful", "angry", "disgusted"}
_SUSTAINED_WINDOW = 5
_SUSTAINED_CONFIDENCE = 0.55

def assess_crisis(text: str, recent_entries: list) -> dict:
    """recent_entries: this user's past journal entries, most recent first, each with
    'emotion' and 'confidence'. Returns {is_crisis, reason} where reason is
    'explicit_language' (acute — surface emergency helplines) or
    'sustained_distress' (pattern over time — suggest professional support) or None."""
    if _CRISIS_RE.search(text):
        return {"is_crisis": True, "reason": "explicit_language"}

    window = recent_entries[:_SUSTAINED_WINDOW]
    if len(window) >= _SUSTAINED_WINDOW and all(
        e.get("emotion") in _NEGATIVE_EMOTIONS and (e.get("confidence") or 0) > _SUSTAINED_CONFIDENCE
        for e in window
    ):
        return {"is_crisis": True, "reason": "sustained_distress"}

    return {"is_crisis": False, "reason": None}

CRISIS_RESOURCES_ACUTE = """If you're in immediate danger, please reach out right now — you don't have to go through this alone:
• iCall — 9152987821 (Mon–Sat, 10am–8pm)
• AASRA — 91-22-27546669 (24/7)
• Vandrevala Foundation — 1860-2662-345 or 1800-2333-330 (24/7)
• KIRAN Mental Health Helpline — 1800-599-0019 (24/7)"""

CRISIS_RESOURCES_SUPPORTIVE = """It might help to talk to someone trained for this, alongside our conversations:
• iCall — 9152987821 (Mon–Sat, 10am–8pm) — free counselling support
• Vandrevala Foundation — 1860-2662-345 (24/7)

Even one conversation with a professional can help more than it seems right now."""
