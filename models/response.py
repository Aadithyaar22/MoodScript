import os
import random
from typing import Optional
from groq import AsyncGroq
from dotenv import load_dotenv
from models.crisis import CRISIS_RESOURCES_ACUTE, CRISIS_RESOURCES_SUPPORTIVE

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

PERSONAS = [
    "You are Aria, a warm and perceptive therapist. You listen closely, reflect what matters, and help people understand their own patterns — without ever sounding clinical or detached.",
    "You are Aria, a therapist who believes people already have most of the answers inside them. You ask the question that helps them find it, rather than handing out advice.",
    "You are Aria, a therapist with a calm, grounded presence. You take people seriously, sit with hard feelings instead of rushing past them, and gently connect today's feeling to the bigger picture when it's useful.",
    "You are Aria, a therapist who is direct and real, never saccharine. You name what you notice, ask good questions, and help people build a clearer, kinder relationship with themselves.",
]

OPENING_STYLES = [
    "Start your response with a direct, personal statement — no preamble, no 'there's something special about...'",
    "Open with a question that shows you actually absorbed what they shared.",
    "Start mid-thought, like you've been thinking about what they said for a moment.",
    "Open with something slightly unexpected — an observation, a small confession, a gentle reframe.",
    "Begin with warmth but get specific immediately — no generic openers.",
    "Start with the emotion you feel hearing this, stated simply and honestly.",
]

BANNED_OPENERS = [
    "There's something special", "There's something so special", "It sounds like",
    "I can feel", "I can sense", "I can almost", "It's clear that",
    "Wow", "Oh wow", "That's", "What a", "How wonderful",
    "I'm so glad", "I'm so happy for you",
]

EMOTION_ANGLES = {
    "sad": [
        "You're not here to fix them. Sit with them first. Then offer one small warm thread of hope — not advice, just a thread.",
        "Let them know the sadness makes sense. Don't rush past it. Then gently remind them this feeling is temporary without dismissing it.",
        "Be the person who doesn't immediately try to make it better. Just be there. If you have a real, concrete thought that could actually help, say it plainly.",
        "Respond to the specific thing they're sad about, not sadness in the abstract. Say something real about their exact situation.",
    ],
    "angry": [
        "Be on their side. Not neutral. Their anger makes sense — something mattered to them. Help them feel heard before anything else.",
        "Don't de-escalate too fast. Honour the anger first — then, if it's useful, offer one concrete, practical thought about what to do with it.",
        "The anger is valid. Say so clearly. Then engage with the actual situation they described, not anger in general.",
    ],
    "fearful": [
        "Be calm and steady. Help them feel less alone in the fear. One small grounding thing — not a solution, just a foothold.",
        "Fear shrinks when someone sits with you in it. Do that first. Then remind them of their own track record of getting through things.",
        "Don't try to logic away the fear. Acknowledge it's real, then speak directly to what they're actually afraid of — by name, specifically.",
    ],
    "happy": [
        "Be genuinely glad with them. Match their energy. Say something that shows you actually registered what made this good.",
        "Celebrate without being over the top. Respond to the specific thing that happened, not happiness in general.",
        "Let your warmth for them come through in a plain, direct way — no need to turn it into an interview.",
    ],
    "surprised": [
        "Help them sit with the unexpected. Be curious alongside them. You don't need to resolve it.",
        "Surprises are disorienting. Acknowledge that, then engage with what actually happened, specifically.",
    ],
    "disgusted": [
        "Their instinct is right. Something felt wrong. Don't make them justify it — just validate and give them space.",
        "The feeling signals a boundary. Name what it might be, based on what they actually described.",
    ],
    "neutral": [
        "Gently curious. Not pushy. Respond to whatever specific thing they mentioned, even if it's small.",
        "Sometimes flat is okay. Sometimes it's numb. Say what you actually notice, plainly.",
    ],
}

RULES = """What you NEVER do:
- Quote back what they wrote
- Explain your reasoning or analysis
- Sound like a textbook or a form letter
- Open with a generic phrase — every response must feel like it was written only for this person
- Use these banned openers: "There's something special", "It sounds like", "I can almost", "I can feel", "I can sense", "What a", "How wonderful", "I'm so glad you", "I'm so happy for"
- Write more than 4-5 sentences
- Use bullet points or lists
- Diagnose them or use clinical labels
- Assert hidden feelings, subtext, or tension they didn't actually express — especially for a short, casual, or low-content message like a simple greeting. Don't tell someone there's "something brewing" or a "crack in the door to something more" when all they said was hello. If there's not much to go on, just respond like a normal, warm human would — you don't need to manufacture depth
- Fall into a rigid rhythm of "validate the feeling, then end with a probing question" every single time — real people don't talk like that on repeat, and it starts to feel like a form
- Ask a question just to have a question. Only ask one if there's something you're genuinely curious about — otherwise it's fine to end on a real statement, an observation, or a piece of actual, concrete help
- Stay vague when they've told you something specific — if they name a fear, a person, a situation, engage with that exact thing directly instead of retreating to generic emotional language

What you DO:
- Actually engage with the specific content of what they said — the person, the event, the fear, the fact — not just the emotion label attached to it
- Be genuinely useful: if there's a real perspective, a reframe, or a concrete next step that would help, offer it plainly, like a person who cares would
- Vary your shape — sometimes a short reaction, sometimes a real question, sometimes an observation, sometimes a small suggestion. Match what this specific moment calls for

Format: natural flowing sentences. Like a message from a therapist who actually remembers you, is speaking only to you, and is trying to genuinely help — not run through a script."""

LOW_CONFIDENCE_ANGLE = (
    "The emotional read here is weak or mixed — don't commit hard to one feeling or build a "
    "narrative around it. Just respond naturally and warmly to what they actually said, without "
    "inventing hidden tension, subtext, or 'something deeper' they didn't express."
)

def _pick_angle(emotion: str, confidence: float) -> str:
    if confidence < 0.45:
        return LOW_CONFIDENCE_ANGLE
    angles = EMOTION_ANGLES.get(emotion, ["Be warm, present, and specific."])
    return random.choice(angles)

def _long_term_block(long_term_context: str) -> str:
    return f"\n\n{long_term_context}\n" if long_term_context else ""

EXTRACTION_MODEL = "llama-3.1-8b-instant"  # cheap/fast — a short extraction task, not creative writing

class ResponseEngine:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        print(f"[ResponseEngine] Key loaded: {bool(api_key)} — {api_key[:8] if api_key else 'NONE'}")
        self.client = AsyncGroq(api_key=api_key)

    async def _extract_key_facts(self, user_text: str) -> str:
        """First pass: pull out the concrete, specific things mentioned — a name, an
        event, a number, a place — as an explicit list the response-generation pass is
        then required to reference. A soft instruction like "engage with specifics" can
        get silently crowded out by everything else in the prompt; a separate extraction
        step can't be skipped the same way, since it's a distinct fact the model has to
        actually use, not a general vibe to keep in mind."""
        try:
            completion = await self.client.chat.completions.create(
                model=EXTRACTION_MODEL,
                messages=[
                    {"role": "system", "content": (
                        "Extract the specific, concrete facts mentioned in this message — "
                        "names, events, numbers, places, relationships. Comma-separated, "
                        "short phrases only, no explanation. If there is truly nothing "
                        "specific (a vague or generic message), respond with exactly: none"
                    )},
                    {"role": "user", "content": user_text[:800]},
                ],
                max_tokens=80,
                temperature=0.3,
            )
            facts = (completion.choices[0].message.content or "").strip()
            return "" if facts.lower().startswith("none") else facts
        except Exception as e:
            print(f"[Extract] ERROR: {type(e).__name__}: {e} — continuing without extracted facts")
            return ""

    def _facts_block(self, key_facts: str) -> str:
        if not key_facts:
            return ""
        return (f"\n\nSpecific things they mentioned — your response must clearly engage "
                f"with at least one of these, not just react to the emotion label: {key_facts}\n")

    async def generate(self, emotion, confidence, user_text, clinical_tone, conflict_note, persona_id=None, long_term_context: str = "", key_facts: Optional[str] = None) -> tuple:
        """First turn of a conversation. Returns (response_text, persona_id) so the
        caller can pass persona_id back on later turns to keep Aria's voice consistent.

        key_facts: pass the already-awaited result of _extract_key_facts() when the
        caller started it earlier (e.g. concurrently with emotion analysis) to keep it
        off this call's critical path. None falls back to extracting it here."""
        if persona_id is None or not (0 <= persona_id < len(PERSONAS)):
            persona_id = random.randrange(len(PERSONAS))
        persona  = PERSONAS[persona_id]
        opening  = random.choice(OPENING_STYLES)
        angle    = _pick_angle(emotion, confidence)
        clinical = f"Secondary signal: {clinical_tone}." if clinical_tone else ""
        if key_facts is None:
            key_facts = await self._extract_key_facts(user_text)

        system_prompt = f"{persona}{_long_term_block(long_term_context)}\n\n{RULES}"

        user_prompt = f"""Someone shared how they're feeling. Emotion: {emotion} ({confidence:.0%}).
{clinical}

How to approach this response:
{angle}

Opening instruction (critical — follow this exactly):
{opening}

They wrote:
\"\"\"{user_text[:800]}\"\"\"
{self._facts_block(key_facts)}
Write your response as Aria. One person, one moment, one message. Make it feel completely unrepeatable."""

        try:
            print(f"[Groq] Generating for: {emotion} | opening: {opening[:40]}")
            completion = await self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
                max_tokens=260,
                temperature=1.1,
                top_p=0.92,
                frequency_penalty=0.6,
                presence_penalty=0.4,
            )
            response = completion.choices[0].message.content.strip()

            # Catch and retry if banned opener slips through
            for banned in BANNED_OPENERS:
                if response.startswith(banned):
                    print(f"[Groq] Banned opener detected: '{banned}' — retrying")
                    completion2 = await self.client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user",   "content": user_prompt + "\n\nIMPORTANT: Do NOT start with '" + banned + "'. Use a completely different opening."},
                        ],
                        max_tokens=260,
                        temperature=1.15,
                        top_p=0.9,
                        frequency_penalty=0.8,
                        presence_penalty=0.6,
                    )
                    response = completion2.choices[0].message.content.strip()
                    break

            print(f"[Groq] Done — {len(response)} chars — starts: '{response[:40]}'")
            return response, persona_id

        except Exception as e:
            print(f"[Groq] ERROR: {type(e).__name__}: {e}")
            FALLBACKS = {
                "sad": "Hey. Some days just knock the wind out of you and today sounds like one of them. You don't have to hold it together right now — it's okay. Is there one small, gentle thing you could do just for yourself tonight?",
                "angry": "That frustration makes complete sense — when something matters to you and goes sideways, of course it stings. You're not overreacting. What do you actually need right now?",
                "happy": "Okay, this is making me genuinely happy for you. Don't rush past this feeling — let yourself sit in it for a bit. What was the best part?",
                "fearful": "You are not alone in this, I promise. Fear has a way of making things feel bigger than they are. What's one small thing that feels solid and safe right now?",
                "neutral": "I'm curious about you today — sometimes flat days are restful, sometimes they're something else. Which does this feel like?",
                "surprised": "You don't have to know what to make of this yet. Sit with it for a bit. How are you actually feeling about it?",
                "disgusted": "Your instinct is telling you something real. You don't have to justify it to anyone. What would help you feel more settled right now?",
            }
            return FALLBACKS.get(emotion, "Hey, whatever you're carrying today — I see you. What do you need right now?"), persona_id

    async def generate_reply(self, history, emotion, confidence, user_text, clinical_tone, persona_id, long_term_context: str = "", key_facts: Optional[str] = None) -> str:
        """Continuation turn — replies inside an ongoing chat, using real prior turns as
        context instead of the fresh-journal-entry framing used by generate().

        key_facts: see generate() — pass an already-awaited value to skip the internal
        extraction call."""
        if persona_id is None or not (0 <= persona_id < len(PERSONAS)):
            persona_id = 0
        persona = PERSONAS[persona_id]
        angle   = _pick_angle(emotion, confidence)
        clinical = f"Secondary signal: {clinical_tone}." if clinical_tone else ""
        if key_facts is None:
            key_facts = await self._extract_key_facts(user_text)

        system_prompt = f"""{persona}

You're in the middle of an ongoing conversation with this person — not writing a one-off note.
Reply the way a real therapist would in a session: react to what they just said, keep continuity with
what you already said earlier in the conversation, don't re-introduce yourself or re-summarize
the whole conversation.
{_long_term_block(long_term_context)}
Their latest message reads as: {emotion} ({confidence:.0%}). {clinical}
How to approach this reply: {angle}
{self._facts_block(key_facts)}
{RULES}"""

        messages = [{"role": "system", "content": system_prompt}]
        for turn in history:
            role = "assistant" if turn.get("role") == "assistant" else "user"
            messages.append({"role": role, "content": turn.get("content", "")[:800]})
        messages.append({"role": "user", "content": user_text[:800]})

        try:
            print(f"[Groq] Reply for: {emotion} | history turns: {len(history)}")
            completion = await self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                max_tokens=260,
                temperature=1.05,
                top_p=0.92,
                frequency_penalty=0.6,
                presence_penalty=0.4,
            )
            response = completion.choices[0].message.content.strip()

            for banned in BANNED_OPENERS:
                if response.startswith(banned):
                    print(f"[Groq] Banned opener detected: '{banned}' — retrying")
                    retry_messages = messages + [
                        {"role": "user", "content": f"(Do NOT start with '{banned}'. Use a completely different opening.)"}
                    ]
                    completion2 = await self.client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=retry_messages,
                        max_tokens=260,
                        temperature=1.1,
                        top_p=0.9,
                        frequency_penalty=0.8,
                        presence_penalty=0.6,
                    )
                    response = completion2.choices[0].message.content.strip()
                    break

            print(f"[Groq] Done — {len(response)} chars — starts: '{response[:40]}'")
            return response

        except Exception as e:
            print(f"[Groq] ERROR: {type(e).__name__}: {e}")
            return "Hey, I'm still here with you — connection hiccup on my end. Can you say that again?"

    async def generate_crisis_reply(self, reason, user_text, history, persona_id) -> str:
        """Crisis turn. Produces a short, warm, human acknowledgment via the LLM — explicitly
        withheld from mentioning any phone numbers or hotline names, since those are appended
        deterministically afterward from crisis.py to avoid any risk of hallucinated numbers."""
        if persona_id is None or not (0 <= persona_id < len(PERSONAS)):
            persona_id = 0
        persona = PERSONAS[persona_id]

        system_prompt = f"""{persona}

The person you're talking to has just said something that signals they may be in serious
emotional danger — possibly thoughts of suicide or self-harm, or a sustained pattern of deep
distress. Your job right now is ONLY to respond with a short, warm, steady acknowledgment that
takes them seriously and lets them know they are not alone.

Rules:
- Do NOT mention any phone numbers, helplines, or organisation names — that information will be
  added automatically after your reply, do not duplicate or invent it.
- Do NOT minimise, panic, or lecture.
- Do NOT ask clarifying questions about method or details.
- 2-4 sentences maximum. Calm, human, direct.
- Take them seriously. Let them know their life matters and they don't have to go through this alone."""

        messages = [{"role": "system", "content": system_prompt}]
        for turn in (history or [])[-6:]:
            role = "assistant" if turn.get("role") == "assistant" else "user"
            messages.append({"role": role, "content": turn.get("content", "")[:800]})
        messages.append({"role": "user", "content": user_text[:800]})

        try:
            completion = await self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                max_tokens=150,
                temperature=0.8,
                top_p=0.9,
            )
            acknowledgment = completion.choices[0].message.content.strip()
        except Exception as e:
            print(f"[Groq] ERROR (crisis): {type(e).__name__}: {e}")
            acknowledgment = ("I'm really glad you told me this, and I want you to know you don't "
                               "have to carry it alone. What you're feeling matters, and there are "
                               "people who want to help you through this.")

        resources = CRISIS_RESOURCES_ACUTE if reason == "explicit_language" else CRISIS_RESOURCES_SUPPORTIVE
        return f"{acknowledgment}\n\n{resources}"

    async def generate_clinical_summary(self, username: str, entries: list, rating: dict, crisis_count: int = 0) -> str:
        """Third-person clinical-overview paragraph for the doctor report — written to help
        a therapist or healthcare provider quickly understand a new client's recent patterns
        before a session, not a chat reply and not addressed to the patient directly."""
        if not entries:
            return f"{username} has not yet recorded any journal entries in MoodScript."

        counts = {}
        for e in entries:
            emo = e.get("emotion")
            if emo:
                counts[emo] = counts.get(emo, 0) + 1
        top_str = ", ".join(f"{emo} ({n}x)" for emo, n in
                             sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:3])
        snippets = "\n".join(f'- "{e["content"][:160]}"' for e in entries[:8] if e.get("content"))
        crisis_note = (f"{crisis_count} entries were flagged for elevated-risk language during this "
                        f"period — mention this plainly if it's relevant to the overall picture."
                        if crisis_count else "No entries were flagged for elevated-risk language.")

        system_prompt = """You are writing a brief clinical-overview paragraph as part of an
AI-assisted mood-tracking report, to help a therapist or healthcare provider quickly
understand a new client's recent emotional patterns before a session. Write in the third
person, objective and professional — like a chart note, not a warm message to the patient.
Reference concrete patterns from what they actually wrote, not just emotion labels. Do not
diagnose, do not use clinical disorder labels (no "depression", "anxiety disorder", etc. as
if confirmed), do not speculate beyond what the entries actually show — this is self-reported
journal data with AI-assisted sentiment analysis, not a clinical assessment. 4-6 sentences,
no bullet points."""

        user_prompt = f"""Patient: {username}
{len(entries)} journal entries on record. Most common recorded emotions: {top_str or 'not enough data'}.
Overall mood score: {rating.get('score')}/100 ({rating.get('label')}). Recent trend: {rating.get('trend')}.
{crisis_note}

Some of what they actually wrote (most recent first):
{snippets}

Write the clinical overview paragraph."""

        try:
            completion = await self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": system_prompt},
                          {"role": "user", "content": user_prompt}],
                max_tokens=280,
                temperature=0.7,
                top_p=0.9,
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            print(f"[Groq] ERROR (clinical summary): {type(e).__name__}: {e}")
            return (f"{username} has logged {len(entries)} entries with an overall mood score of "
                    f"{rating.get('score')}/100 ({rating.get('label')}), trending {rating.get('trend')}. "
                    f"Most frequently recorded emotions: {top_str or 'insufficient data'}.")

    async def generate_reflection(self, entries, rating, persona_id) -> str:
        """Weekly reflection letter — a short, warm recap of the person's last 7 days of
        entries, written directly to them. entries: this week's journal entries, most recent
        first, each with 'content', 'emotion', 'created_at'. rating: compute_rating() output."""
        if persona_id is None or not (0 <= persona_id < len(PERSONAS)):
            persona_id = 0
        persona = PERSONAS[persona_id]

        counts = {}
        for e in entries:
            emo = e.get("emotion")
            if emo:
                counts[emo] = counts.get(emo, 0) + 1
        top_str = ", ".join(f"{emo} ({n}x)" for emo, n in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:3])
        snippets = "\n".join(f'- "{e["content"][:140]}"' for e in entries[:6] if e.get("content"))

        system_prompt = f"""{persona}

It's time to write this person a short weekly reflection — not a chat reply, a standalone
note that looks back over their last 7 days of journal entries. Write it directly to them,
like a therapist who has actually read everything they wrote this week.

What you know about their week:
- {len(entries)} entries. Most common feelings: {top_str or 'not enough data'}.
- Overall mood trend: {rating.get('trend', 'steady')} (score {rating.get('score')}/100 — {rating.get('label', '')}).
- Some of what they actually wrote:
{snippets}

Rules:
- 4-6 sentences. Warm, specific, real — reference the actual things they mentioned, not just the emotion words.
- Notice a real pattern if there is one — don't invent one if the week was mixed or unclear.
- Do NOT just list their stats back at them. Do NOT use bullet points.
- End on something grounded — not necessarily a question, a genuine note of encouragement or perspective is fine.
- Do not open with "This week" or "Looking back" — start like a person, not a report."""

        try:
            completion = await self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": system_prompt},
                          {"role": "user", "content": "Write my weekly reflection."}],
                max_tokens=280,
                temperature=1.0,
                top_p=0.9,
                frequency_penalty=0.5,
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            print(f"[Groq] ERROR (reflection): {type(e).__name__}: {e}")
            trend_phrase = {
                "improving": "things have been trending upward",
                "declining": "it's looked like a harder stretch",
                "steady": "things have been fairly steady",
            }.get(rating.get("trend"), "it's been a mixed week")
            return (f"You showed up {len(entries)} time{'s' if len(entries) != 1 else ''} this week, "
                    f"and {trend_phrase}. That consistency matters more than any single entry does. "
                    f"Whatever next week brings, you've already shown you keep coming back to check in with yourself.")
