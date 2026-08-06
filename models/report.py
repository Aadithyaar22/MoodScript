import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
)

from models.rating import compute_rating

EMOTION_ORDER = ["happy", "sad", "angry", "fearful", "surprised", "disgusted", "neutral"]
CLINICAL_TONE_ORDER = ["depression", "anxiety", "stress", "positive", "confusion", "curiosity"]

BRAND_PURPLE = colors.HexColor("#5b3f8f")
BRAND_TEAL = colors.HexColor("#1a8c7f")
BRAND_RED = colors.HexColor("#b0342d")
LIGHT_GREY = colors.HexColor("#f2f0f7")

DISCLAIMER = (
    "This report summarizes self-reported journal entries and AI-assisted sentiment "
    "analysis from the MoodScript app. It is not a clinical diagnosis or a substitute "
    "for professional evaluation — please use it as a conversation aid with a qualified "
    "healthcare provider."
)


def _fmt_date(iso_str: str) -> str:
    try:
        return datetime.fromisoformat(iso_str.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except Exception:
        return iso_str[:10] if iso_str else "unknown"


def _report_data(entries: list) -> dict:
    """Shared aggregation used by both the txt and PDF report builders."""
    chrono = list(reversed(entries))  # oldest first
    rating = compute_rating(entries)
    total = len(entries)

    emotion_counts, tone_counts, crisis_dates = {}, {}, []
    for e in entries:
        emo = e.get("emotion")
        if emo:
            emotion_counts[emo] = emotion_counts.get(emo, 0) + 1
        tone = e.get("clinical_tone")
        if tone:
            tone_counts[tone] = tone_counts.get(tone, 0) + 1
        if e.get("crisis_flag"):
            crisis_dates.append(_fmt_date(e["created_at"]))

    return {
        "chrono": chrono,
        "rating": rating,
        "total": total,
        "emotion_counts": emotion_counts,
        "tone_counts": tone_counts,
        "crisis_dates": crisis_dates,
        "period_start": _fmt_date(chrono[0]["created_at"]) if chrono else None,
        "period_end": _fmt_date(chrono[-1]["created_at"]) if chrono else None,
    }


def build_doctor_report(username: str, entries: list) -> str:
    """Plain-text mood summary intended to be shared with a healthcare provider."""
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")

    if not entries:
        return (
            f"MoodScript — Mood Summary Report\n"
            f"Patient: {username}\nGenerated: {generated}\n\n"
            f"No journal entries recorded yet."
        )

    d = _report_data(entries)
    rating, total = d["rating"], d["total"]

    lines = []
    lines.append("MoodScript — Mood Summary Report")
    lines.append(f"Patient: {username}")
    lines.append(f"Generated: {generated}")
    lines.append(f"Reporting period: {d['period_start']} to {d['period_end']} ({total} entries)")
    lines.append("")
    lines.append(DISCLAIMER)
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
        if emo in d["emotion_counts"]:
            n = d["emotion_counts"][emo]
            lines.append(f"  {emo:<12} {n:>3}  ({n/total*100:.0f}%)")
    for emo, n in d["emotion_counts"].items():
        if emo not in EMOTION_ORDER:
            lines.append(f"  {emo:<12} {n:>3}  ({n/total*100:.0f}%)")
    lines.append("")

    if d["tone_counts"]:
        lines.append("-" * 60)
        lines.append("LANGUAGE PATTERN SIGNALS (secondary signal, not a diagnosis)")
        lines.append("-" * 60)
        for tone in CLINICAL_TONE_ORDER:
            if tone in d["tone_counts"]:
                lines.append(f"  {tone:<12} {d['tone_counts'][tone]:>3} entries")
        for tone, n in d["tone_counts"].items():
            if tone not in CLINICAL_TONE_ORDER:
                lines.append(f"  {tone:<12} {n:>3} entries")
        lines.append("")

    lines.append("-" * 60)
    lines.append("SAFETY FLAGS")
    lines.append("-" * 60)
    if d["crisis_dates"]:
        n = len(d["crisis_dates"])
        lines.append(f"  {n} entr{'y' if n == 1 else 'ies'} flagged for elevated-risk language on:")
        lines.append(f"  {', '.join(d['crisis_dates'])}")
    else:
        lines.append("  No safety flags recorded in this period.")
    lines.append("")

    lines.append("-" * 60)
    lines.append("JOURNAL ENTRIES (chronological)")
    lines.append("-" * 60)
    for e in d["chrono"]:
        date = _fmt_date(e["created_at"])
        emo = e.get("emotion") or "unrated"
        conf = e.get("confidence")
        conf_str = f", {conf*100:.0f}% confidence" if isinstance(conf, (int, float)) else ""
        flag = "  [SAFETY FLAG]" if e.get("crisis_flag") else ""
        lines.append(f"\n{date} — {emo}{conf_str}{flag}")
        lines.append(f"  \"{e['content']}\"")

    return "\n".join(lines)


def _pdf_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        "MSTitle", parent=styles["Title"], fontSize=26, leading=32, textColor=BRAND_PURPLE,
        spaceAfter=8, fontName="Helvetica-Bold", alignment=0,
    ))
    styles.add(ParagraphStyle(
        "MSSubtitle", parent=styles["Normal"], fontSize=12, leading=16,
        textColor=colors.HexColor("#555555"), spaceAfter=14,
    ))
    styles.add(ParagraphStyle(
        "MSSection", parent=styles["Heading2"], fontSize=12.5, textColor=BRAND_PURPLE,
        spaceBefore=16, spaceAfter=6, fontName="Helvetica-Bold",
    ))
    styles.add(ParagraphStyle(
        "MSBody", parent=styles["Normal"], fontSize=10, leading=15,
    ))
    styles.add(ParagraphStyle(
        "MSDisclaimer", parent=styles["Normal"], fontSize=8.5, leading=12,
        textColor=colors.HexColor("#666666"), fontName="Helvetica-Oblique",
    ))
    styles.add(ParagraphStyle(
        "MSEntryDate", parent=styles["Normal"], fontSize=9, textColor=BRAND_PURPLE,
        fontName="Helvetica-Bold", spaceBefore=8,
    ))
    styles.add(ParagraphStyle(
        "MSEntryBody", parent=styles["Normal"], fontSize=9.5, leading=13,
        textColor=colors.HexColor("#222222"), leftIndent=10, spaceAfter=4,
    ))
    return styles


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#888888"))
    canvas.drawString(0.75 * inch, 0.5 * inch,
                       "MoodScript — Confidential Mood & Wellness Summary — Not a clinical diagnosis")
    canvas.drawRightString(letter[0] - 0.75 * inch, 0.5 * inch, f"Page {doc.page}")
    canvas.restoreState()


def build_doctor_report_pdf(username: str, entries: list, clinical_summary: str) -> bytes:
    """Hospital-style PDF mood summary report — MoodScript-branded, patient information,
    an AI-generated clinical overview paragraph, and structured mood/safety/entry sections."""
    styles = _pdf_styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        topMargin=0.75 * inch, bottomMargin=0.85 * inch,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
    )
    story = []
    generated = datetime.now().strftime("%B %d, %Y — %H:%M")

    story.append(Paragraph("MoodScript", styles["MSTitle"]))
    story.append(Paragraph("Mood &amp; Wellness Summary Report", styles["MSSubtitle"]))
    story.append(HRFlowable(width="100%", thickness=1.4, color=BRAND_PURPLE, spaceAfter=12))

    if not entries:
        story.append(Paragraph(f"<b>Patient:</b> {username}", styles["MSBody"]))
        story.append(Paragraph(f"<b>Generated:</b> {generated}", styles["MSBody"]))
        story.append(Spacer(1, 12))
        story.append(Paragraph("No journal entries recorded yet.", styles["MSBody"]))
        doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
        return buf.getvalue()

    d = _report_data(entries)
    rating, total = d["rating"], d["total"]

    # ---- Patient information ----
    story.append(Paragraph("PATIENT INFORMATION", styles["MSSection"]))
    info_table = Table([
        ["Patient Name", username, "Report Generated", generated],
        ["Reporting Period", f"{d['period_start']} to {d['period_end']}", "Total Entries", str(total)],
    ], colWidths=[1.3 * inch, 2.1 * inch, 1.5 * inch, 1.5 * inch])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("TEXTCOLOR", (0, 0), (0, -1), BRAND_PURPLE),
        ("TEXTCOLOR", (2, 0), (2, -1), BRAND_PURPLE),
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GREY),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d8d0e8")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d8d0e8")),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 8))
    story.append(Paragraph(DISCLAIMER, styles["MSDisclaimer"]))

    # ---- Clinical overview (AI-generated narrative) ----
    story.append(Paragraph("CLINICAL OVERVIEW", styles["MSSection"]))
    story.append(Paragraph(clinical_summary, styles["MSBody"]))

    # ---- Overall mood ----
    story.append(Paragraph("OVERALL MOOD ASSESSMENT", styles["MSSection"]))
    mood_table = Table([
        ["Mood Score", f"{rating['score']}/100", "Assessment", rating["label"]],
        ["Recent Trend", rating["trend"].capitalize(), "", ""],
    ], colWidths=[1.3 * inch, 1.3 * inch, 1.3 * inch, 2.5 * inch])
    mood_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("SPAN", (1, 1), (3, 1)),
        ("LINEBELOW", (0, 0), (-1, 0), 0.4, colors.HexColor("#dddddd")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(mood_table)

    # ---- Emotion distribution ----
    story.append(Paragraph("EMOTION DISTRIBUTION", styles["MSSection"]))
    emo_rows = [["Emotion", "Count", "Share"]]
    ordered_emotions = [e for e in EMOTION_ORDER if e in d["emotion_counts"]]
    ordered_emotions += [e for e in d["emotion_counts"] if e not in EMOTION_ORDER]
    for emo in ordered_emotions:
        n = d["emotion_counts"][emo]
        emo_rows.append([emo.capitalize(), str(n), f"{n/total*100:.0f}%"])
    emo_table = Table(emo_rows, colWidths=[2.2 * inch, 1.2 * inch, 1.2 * inch])
    emo_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_PURPLE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GREY]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dddddd")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(emo_table)

    # ---- Language pattern signals ----
    if d["tone_counts"]:
        story.append(Paragraph("LANGUAGE PATTERN SIGNALS", styles["MSSection"]))
        story.append(Paragraph(
            "Secondary signal derived from language patterns — not a diagnosis.",
            styles["MSDisclaimer"],
        ))
        story.append(Spacer(1, 4))
        tone_rows = [["Signal", "Entries"]]
        ordered_tones = [t for t in CLINICAL_TONE_ORDER if t in d["tone_counts"]]
        ordered_tones += [t for t in d["tone_counts"] if t not in CLINICAL_TONE_ORDER]
        for tone in ordered_tones:
            tone_rows.append([tone.capitalize(), str(d["tone_counts"][tone])])
        tone_table = Table(tone_rows, colWidths=[2.2 * inch, 1.2 * inch])
        tone_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BRAND_TEAL),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9.5),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GREY]),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dddddd")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(tone_table)

    # ---- Safety flags ----
    story.append(Paragraph("SAFETY FLAGS", styles["MSSection"]))
    if d["crisis_dates"]:
        n = len(d["crisis_dates"])
        flag_style = ParagraphStyle("MSFlag", parent=styles["MSBody"], textColor=BRAND_RED, fontName="Helvetica-Bold")
        story.append(Paragraph(
            f"{n} entr{'y' if n == 1 else 'ies'} flagged for elevated-risk language on: "
            f"{', '.join(d['crisis_dates'])}", flag_style,
        ))
    else:
        story.append(Paragraph("No safety flags recorded in this period.", styles["MSBody"]))

    # ---- Journal entry log ----
    story.append(Paragraph("JOURNAL ENTRY LOG (CHRONOLOGICAL)", styles["MSSection"]))
    for e in d["chrono"]:
        date = _fmt_date(e["created_at"])
        emo = e.get("emotion") or "unrated"
        conf = e.get("confidence")
        conf_str = f" · {conf*100:.0f}% confidence" if isinstance(conf, (int, float)) else ""
        flag_str = " · <b><font color='#b0342d'>SAFETY FLAG</font></b>" if e.get("crisis_flag") else ""
        story.append(Paragraph(f"{date} — {emo.capitalize()}{conf_str}{flag_str}", styles["MSEntryDate"]))
        content = (e.get("content") or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        story.append(Paragraph(f"“{content}”", styles["MSEntryBody"]))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()
