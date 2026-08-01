EMOTION_VALENCE = {
    "happy": 1.0, "surprised": 0.4, "neutral": 0.0,
    "disgusted": -0.4, "fearful": -0.7, "sad": -0.8, "angry": -0.6,
}
RECENCY_DECAY = 0.97  # per entry, most recent first

def compute_rating(entries: list) -> dict:
    """entries: journal entries (most recent first), each with 'emotion' and 'confidence'."""
    if not entries:
        return {"score": None, "trend": "steady", "label": "No entries yet", "entry_count": 0}

    weighted_sum = 0.0
    weight_total = 0.0
    for i, e in enumerate(entries):
        recency_weight = RECENCY_DECAY ** i
        conf = e.get("confidence") or 0.5
        val = EMOTION_VALENCE.get(e.get("emotion"), 0.0)
        w = recency_weight * conf
        weighted_sum += val * w
        weight_total += w
    avg_valence = weighted_sum / weight_total if weight_total else 0.0
    score = round((avg_valence + 1) / 2 * 100)

    window = entries[:20]
    half = len(window) // 2 or 1
    recent, older = window[:half], (window[half:] or window[:half])

    def _avg(chunk):
        return sum(EMOTION_VALENCE.get(e.get("emotion"), 0.0) for e in chunk) / len(chunk) if chunk else 0.0

    diff = _avg(recent) - _avg(older)
    trend = "improving" if diff > 0.08 else "declining" if diff < -0.08 else "steady"

    if score >= 70:
        label = "Doing well"
    elif score >= 50:
        label = "Holding steady"
    elif score >= 30:
        label = "Struggling a bit"
    else:
        label = "Having a hard time"

    return {"score": score, "trend": trend, "label": label, "entry_count": len(entries)}


def summarize_history(entries: list) -> str:
    """Compact narrative summary of a user's past entries, for injecting into the LLM prompt
    as long-term memory/context. entries: most recent first, excluding the current conversation."""
    if not entries:
        return ""

    counts = {}
    for e in entries:
        emo = e.get("emotion")
        if emo:
            counts[emo] = counts.get(emo, 0) + 1
    top = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:3]
    top_str = ", ".join(f"{emo} ({n}x)" for emo, n in top)

    rating = compute_rating(entries)
    trend_phrase = {
        "improving": "their mood has been trending upward recently",
        "declining": "their mood has been trending downward recently",
        "steady": "their mood has been fairly steady",
    }[rating["trend"]]

    recent_snippets = [e["content"][:120] for e in entries[:3] if e.get("content")]
    snippet_block = "\n".join(f'- "{s}"' for s in recent_snippets)

    return f"""LONG-TERM CONTEXT (from this person's past journal entries — use this to notice patterns, don't just repeat it back):
They have {len(entries)} prior entries. Most common feelings: {top_str}. Overall, {trend_phrase}.
A few recent things they've shared:
{snippet_block}"""
