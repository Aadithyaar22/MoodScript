from datetime import datetime
from models.rating import compute_rating

EMOTION_ORDER = ["happy", "sad", "angry", "fearful", "surprised", "disgusted", "neutral"]
CLINICAL_TONE_ORDER = ["depression", "anxiety", "stress", "positive", "confusion", "curiosity"]

def _fmt_date(iso_str: str) -> str:
    try:
        return datetime.fromisoformat(iso_str.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except Exception:
        return iso_str[:10] if iso_str else "unknown"

def build_doctor_report(username: str, entries: list) -> str:
    """entries: this user's journal entries, most recent first, each with 'content',
    'emotion', 'confidence', 'clinical_tone', 'crisis_flag', 'created_at'.
    Produces a plain-text mood summary intended to be shared with a healthcare provider —
    a self-reported/AI-assisted summary, not a diagnosis."""
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")

    if not entries:
        return (
            f"MoodScript — Mood Summary Report\n"
            f"Patient: {username}\nGenerated: {generated}\n\n"
            f"No journal entries recorded yet."
        )

    chrono = list(reversed(entries))  # oldest first, for date range + trend readability
    period_start = _fmt_date(chrono[0]["created_at"])
    period_end = _fmt_date(chrono[-1]["created_at"])
    rating = compute_rating(entries)

    emotion_counts = {}
    tone_counts = {}
    crisis_dates = []
    for e in entries:
        emo = e.get("emotion")
        if emo:
            emotion_counts[emo] = emotion_counts.get(emo, 0) + 1
        tone = e.get("clinical_tone")
        if tone:
            tone_counts[tone] = tone_counts.get(tone, 0) + 1
        if e.get("crisis_flag"):
            crisis_dates.append(_fmt_date(e["created_at"]))

    total = len(entries)
    lines = []
    lines.append("MoodScript — Mood Summary Report")
    lines.append(f"Patient: {username}")
    lines.append(f"Generated: {generated}")
    lines.append(f"Reporting period: {period_start} to {period_end} ({total} entries)")
    lines.append("")
    lines.append(
        "This report summarizes self-reported journal entries and AI-assisted sentiment "
        "analysis from the MoodScript app. It is not a clinical diagnosis or a substitute "
        "for professional evaluation — please use it as a conversation aid with a qualified "
        "healthcare provider."
    )
    lines.append("")
    lines.append("-" * 60)
    lines.append("OVERALL MOOD")
    lines.append("-" * 60)
    lines.append(f"Score: {rating['score']}/100 ({rating['label']})")
    lines.append(f"Recent trend: {rating['trend']}")
    lines.append("")
    lines.append("-" * 60)
    lines.append("EMOTION DISTRIBUTION")
    lines.append("-" * 60)
    for emo in EMOTION_ORDER:
        if emo in emotion_counts:
            n = emotion_counts[emo]
            lines.append(f"  {emo:<12} {n:>3}  ({n/total*100:.0f}%)")
    for emo, n in emotion_counts.items():
        if emo not in EMOTION_ORDER:
            lines.append(f"  {emo:<12} {n:>3}  ({n/total*100:.0f}%)")
    lines.append("")

    if tone_counts:
        lines.append("-" * 60)
        lines.append("LANGUAGE PATTERN SIGNALS (secondary signal, not a diagnosis)")
        lines.append("-" * 60)
        for tone in CLINICAL_TONE_ORDER:
            if tone in tone_counts:
                lines.append(f"  {tone:<12} {tone_counts[tone]:>3} entries")
        for tone, n in tone_counts.items():
            if tone not in CLINICAL_TONE_ORDER:
                lines.append(f"  {tone:<12} {n:>3} entries")
        lines.append("")

    lines.append("-" * 60)
    lines.append("SAFETY FLAGS")
    lines.append("-" * 60)
    if crisis_dates:
        lines.append(f"  {len(crisis_dates)} entr{'y' if len(crisis_dates) == 1 else 'ies'} flagged for elevated-risk language on:")
        lines.append(f"  {', '.join(crisis_dates)}")
    else:
        lines.append("  No safety flags recorded in this period.")
    lines.append("")

    lines.append("-" * 60)
    lines.append("JOURNAL ENTRIES (chronological)")
    lines.append("-" * 60)
    for e in chrono:
        date = _fmt_date(e["created_at"])
        emo = e.get("emotion") or "unrated"
        conf = e.get("confidence")
        conf_str = f", {conf*100:.0f}% confidence" if isinstance(conf, (int, float)) else ""
        flag = "  [SAFETY FLAG]" if e.get("crisis_flag") else ""
        lines.append(f"\n{date} — {emo}{conf_str}{flag}")
        lines.append(f"  \"{e['content']}\"")

    return "\n".join(lines)
