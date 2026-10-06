"""In-memory stand-ins for everything the orchestrator talks to, so the API tests are fast,
deterministic and can never reach Neon, Groq, or the model services."""
import itertools
import json
import re
from datetime import datetime, timezone

import httpx

EMOTIONS = ["angry", "disgusted", "fearful", "happy", "neutral", "sad", "surprised"]


def dist(top, p=0.7):
    """A probability distribution with `top` carrying mass p and the rest shared evenly."""
    rest = (1.0 - p) / (len(EMOTIONS) - 1)
    return {e: (p if e == top else rest) for e in EMOTIONS}


def _now():
    return datetime.now(timezone.utc).isoformat()


class FakeDB:
    """Mirrors database.db.MoodDatabase (same method names and return shapes)."""

    def __init__(self):
        self.users, self.conversations, self.messages, self.reflections = {}, {}, [], {}
        self._uid, self._cid, self._mid = (itertools.count(1) for _ in range(3))

    # users
    def create_user(self, username, password_hash=None, google_id=None):
        uid = next(self._uid)
        self.users[uid] = {"id": uid, "username": username, "password_hash": password_hash,
                           "google_id": google_id, "created_at": _now()}
        return uid

    def get_user_by_username(self, username):
        return next((dict(u) for u in self.users.values() if u["username"] == username), None)

    def get_user_by_google_id(self, google_id):
        return next((dict(u) for u in self.users.values() if u["google_id"] == google_id), None)

    def link_google_id(self, user_id, google_id):
        self.users[user_id]["google_id"] = google_id

    def get_user_by_id(self, user_id):
        u = self.users.get(user_id)
        return dict(u) if u else None

    # conversations
    def create_conversation(self, user_id, persona_id):
        cid = next(self._cid)
        self.conversations[cid] = {"id": cid, "user_id": user_id, "persona_id": persona_id,
                                   "started_at": _now()}
        return cid

    def get_conversation(self, conversation_id, user_id):
        c = self.conversations.get(conversation_id)
        return dict(c) if c and c["user_id"] == user_id else None

    def set_conversation_persona(self, conversation_id, persona_id):
        self.conversations[conversation_id]["persona_id"] = persona_id

    def delete_conversation(self, conversation_id, user_id):
        self.messages = [m for m in self.messages
                         if not (m["conversation_id"] == conversation_id and m["user_id"] == user_id)]
        c = self.conversations.get(conversation_id)
        if c and c["user_id"] == user_id:
            del self.conversations[conversation_id]

    def list_conversations(self, user_id, limit=50):
        out = []
        for c in sorted((c for c in self.conversations.values() if c["user_id"] == user_id),
                        key=lambda c: c["id"], reverse=True)[:limit]:
            msgs = [m for m in self.messages if m["conversation_id"] == c["id"]]
            first_user = next((m["content"] for m in msgs if m["role"] == "user"), None)
            out.append({"id": c["id"], "started_at": c["started_at"], "persona_id": c["persona_id"],
                        "opening_line": first_user, "message_count": len(msgs)})
        return out

    # messages
    def add_message(self, conversation_id, user_id, role, content, emotion=None, confidence=None,
                    face_emotion=None, clinical_tone=None, resolution_reason=None, crisis_flag=False):
        self.messages.append({
            "id": next(self._mid), "conversation_id": conversation_id, "user_id": user_id,
            "role": role, "content": content, "emotion": emotion, "confidence": confidence,
            "face_emotion": face_emotion, "clinical_tone": clinical_tone,
            "resolution_reason": resolution_reason, "crisis_flag": int(crisis_flag),
            "created_at": _now()})

    def get_conversation_messages(self, conversation_id, user_id):
        return [dict(m) for m in self.messages
                if m["conversation_id"] == conversation_id and m["user_id"] == user_id]

    def get_user_journal_entries(self, user_id, exclude_conversation_id=None, limit=200):
        rows = [m for m in self.messages
                if m["user_id"] == user_id and m["role"] == "user" and m["emotion"] is not None
                and m["conversation_id"] != exclude_conversation_id]
        return [dict(m) for m in sorted(rows, key=lambda m: m["id"], reverse=True)[:limit]]

    # reflections
    def get_reflection(self, user_id, week_key):
        return self.reflections.get((user_id, week_key))

    def save_reflection(self, user_id, week_key, content, entry_count):
        self.reflections[(user_id, week_key)] = {"content": content, "entry_count": entry_count}

    # account
    def delete_user_data(self, user_id):
        self.messages = [m for m in self.messages if m["user_id"] != user_id]
        self.conversations = {k: c for k, c in self.conversations.items() if c["user_id"] != user_id}
        self.reflections = {k: v for k, v in self.reflections.items() if k[0] != user_id}
        self.users.pop(user_id, None)

    def get_history(self, user_id, limit=30):
        return [{"id": e["id"], "timestamp": e["created_at"], "emotion": e["emotion"],
                 "face_emotion": e["face_emotion"], "text_emotion": e["emotion"],
                 "face_confidence": None, "text_confidence": e["confidence"],
                 "resolution_reason": e["resolution_reason"], "journal_snippet": e["content"][:100],
                 "clinical_tone": e["clinical_tone"]}
                for e in self.get_user_journal_entries(user_id, limit=limit)]

    # test helper
    def seed_entries(self, user_id, emotions, confidence=0.9):
        """Insert past journal entries oldest-first, so emotions[-1] ends up most recent."""
        cid = self.create_conversation(user_id, 0)
        for i, emo in enumerate(emotions):
            self.add_message(cid, user_id, "user", f"seed entry {i}", emotion=emo, confidence=confidence)
        return cid


class FakeResponseEngine:
    """Replaces the Groq-backed ResponseEngine; records which generation path was taken."""

    def __init__(self):
        self.calls = []

    async def _extract_key_facts(self, text):
        self.calls.append("extract_key_facts")
        return ["a fact"]

    async def generate(self, **kw):
        self.calls.append("generate")
        return "Aria first reply", 3

    async def generate_reply(self, **kw):
        self.calls.append("generate_reply")
        return "Aria follow-up reply"

    async def generate_crisis_reply(self, **kw):
        self.calls.append("generate_crisis_reply")
        self.last_crisis_reason = kw.get("reason")
        return "Aria crisis reply"

    async def generate_reflection(self, entries, rating, persona_id):
        self.calls.append("generate_reflection")
        return "Weekly reflection letter"

    async def generate_clinical_summary(self, *a, **kw):
        self.calls.append("generate_clinical_summary")
        return "Clinical summary text"


class StubServices:
    """Stands in for the text and face services behind httpx. The text emotion is chosen by
    keyword so a test can steer it from the message; the face emotion is set per test."""

    KEYWORDS = {"sad": "sad", "happy": "happy", "proud": "happy", "angry": "angry",
                "afraid": "fearful", "anxious": "fearful"}

    def __init__(self):
        self.text_emotion = None          # force a text emotion; None = pick from keywords
        self.face_emotion = "happy"
        self.text_p, self.face_p = 0.7, 0.7
        self.text_down = False
        self.face_down = False
        self.requests = []

    def _text_for(self, message):
        if self.text_emotion:
            return self.text_emotion
        low = message.lower()
        return next((v for k, v in self.KEYWORDS.items() if k in low), "neutral")

    def handler(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content or b"{}")
        self.requests.append((request.url.path, body))
        if request.url.path == "/analyze":
            if self.text_down:
                return httpx.Response(503, json={"detail": "text service down"})
            emo = self._text_for(body["text"])
            d = dist(emo, self.text_p)
            return httpx.Response(200, json={
                "text_result": {"dominant_emotion": emo, "confidence": d[emo], "all_scores": d,
                                "emotion_arc": [{"sentence": body["text"][:40], "emotion": emo}],
                                "clinical_tone": None},
                # same shape as the real text service's xai.explain(): what the "why?" panel reads
                "xai_result": {"key_sentence": body["text"][:60],
                               "top_words": [{"word": "proud", "direction": "positive"},
                                             {"word": "tired", "direction": "negative"}],
                               "text_confidence_array": d}})
        if request.url.path == "/predict":
            if self.face_down:
                return httpx.Response(500, json={"detail": "face service down"})
            d = dist(self.face_emotion, self.face_p)
            return httpx.Response(200, json={"emotion": self.face_emotion,
                                             "confidence": d[self.face_emotion], "all_scores": d})
        return httpx.Response(404)
