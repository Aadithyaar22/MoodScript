import os
import psycopg2
import psycopg2.extras
from datetime import datetime, timezone

DATABASE_URL = os.getenv("DATABASE_URL")

def _connect():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    return conn

def _now():
    return datetime.now(timezone.utc).isoformat()

class MoodDatabase:
    def __init__(self):
        self._init_db()

    def _init_db(self):
        conn = _connect()
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                persona_id INTEGER,
                started_at TEXT NOT NULL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                conversation_id INTEGER NOT NULL REFERENCES conversations(id),
                user_id INTEGER NOT NULL REFERENCES users(id),
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                emotion TEXT,
                confidence REAL,
                face_emotion TEXT,
                clinical_tone TEXT,
                resolution_reason TEXT,
                crisis_flag INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS reflections (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                week_key TEXT NOT NULL,
                content TEXT NOT NULL,
                entry_count INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(user_id, week_key)
            )
        """)
        conn.commit()
        conn.close()

    # ---------- users ----------
    def create_user(self, username: str, password_hash: str) -> int:
        conn = _connect()
        c = conn.cursor()
        c.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (%s, %s, %s) RETURNING id",
            (username, password_hash, _now()),
        )
        user_id = c.fetchone()["id"]
        conn.commit()
        conn.close()
        return user_id

    def get_user_by_username(self, username: str):
        conn = _connect()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = %s", (username,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_user_by_id(self, user_id: int):
        conn = _connect()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None

    # ---------- conversations ----------
    def create_conversation(self, user_id: int, persona_id):
        conn = _connect()
        c = conn.cursor()
        c.execute(
            "INSERT INTO conversations (user_id, persona_id, started_at) VALUES (%s, %s, %s) RETURNING id",
            (user_id, persona_id, _now()),
        )
        conv_id = c.fetchone()["id"]
        conn.commit()
        conn.close()
        return conv_id

    def get_conversation(self, conversation_id: int, user_id: int):
        conn = _connect()
        c = conn.cursor()
        c.execute("SELECT * FROM conversations WHERE id = %s AND user_id = %s", (conversation_id, user_id))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None

    def set_conversation_persona(self, conversation_id: int, persona_id: int):
        conn = _connect()
        c = conn.cursor()
        c.execute("UPDATE conversations SET persona_id = %s WHERE id = %s", (persona_id, conversation_id))
        conn.commit()
        conn.close()

    def list_conversations(self, user_id: int, limit: int = 50):
        conn = _connect()
        c = conn.cursor()
        c.execute("""
            SELECT c.id, c.started_at, c.persona_id,
                   (SELECT content FROM messages m WHERE m.conversation_id = c.id AND m.role='user'
                        ORDER BY m.id ASC LIMIT 1) AS opening_line,
                   (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) AS message_count
            FROM conversations c
            WHERE c.user_id = %s
            ORDER BY c.started_at DESC
            LIMIT %s
        """, (user_id, limit))
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # ---------- messages ----------
    def add_message(self, conversation_id: int, user_id: int, role: str, content: str,
                     emotion=None, confidence=None, face_emotion=None, clinical_tone=None,
                     resolution_reason=None, crisis_flag=False):
        conn = _connect()
        c = conn.cursor()
        c.execute("""
            INSERT INTO messages
            (conversation_id, user_id, role, content, emotion, confidence, face_emotion,
             clinical_tone, resolution_reason, crisis_flag, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (conversation_id, user_id, role, content, emotion, confidence, face_emotion,
              clinical_tone, resolution_reason, int(crisis_flag), _now()))
        conn.commit()
        conn.close()

    def get_conversation_messages(self, conversation_id: int, user_id: int):
        conn = _connect()
        c = conn.cursor()
        c.execute("""
            SELECT * FROM messages WHERE conversation_id = %s AND user_id = %s ORDER BY id ASC
        """, (conversation_id, user_id))
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_user_journal_entries(self, user_id: int, exclude_conversation_id=None, limit: int = 200):
        """All logged user-authored, emotion-tagged messages — the person's full mood journal."""
        conn = _connect()
        c = conn.cursor()
        if exclude_conversation_id is not None:
            c.execute("""
                SELECT * FROM messages
                WHERE user_id = %s AND role = 'user' AND emotion IS NOT NULL AND conversation_id != %s
                ORDER BY created_at DESC LIMIT %s
            """, (user_id, exclude_conversation_id, limit))
        else:
            c.execute("""
                SELECT * FROM messages
                WHERE user_id = %s AND role = 'user' AND emotion IS NOT NULL
                ORDER BY created_at DESC LIMIT %s
            """, (user_id, limit))
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # ---------- reflections ----------
    def get_reflection(self, user_id: int, week_key: str):
        conn = _connect()
        c = conn.cursor()
        c.execute("SELECT * FROM reflections WHERE user_id = %s AND week_key = %s", (user_id, week_key))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None

    def save_reflection(self, user_id: int, week_key: str, content: str, entry_count: int):
        conn = _connect()
        c = conn.cursor()
        c.execute("""
            INSERT INTO reflections (user_id, week_key, content, entry_count, created_at)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (user_id, week_key) DO UPDATE SET content=excluded.content, entry_count=excluded.entry_count
        """, (user_id, week_key, content, entry_count, _now()))
        conn.commit()
        conn.close()

    # ---------- account ----------
    def delete_user_data(self, user_id: int):
        conn = _connect()
        c = conn.cursor()
        c.execute("DELETE FROM messages WHERE user_id = %s", (user_id,))
        c.execute("DELETE FROM conversations WHERE user_id = %s", (user_id,))
        c.execute("DELETE FROM reflections WHERE user_id = %s", (user_id,))
        c.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        conn.close()

    def get_history(self, user_id: int, limit: int = 30) -> list:
        """Flat mood-log view (most recent first) shaped for the existing dashboard/sidebar UI."""
        entries = self.get_user_journal_entries(user_id, limit=limit)
        return [
            {
                "id": e["id"],
                "timestamp": e["created_at"],
                "emotion": e["emotion"],
                "face_emotion": e["face_emotion"],
                "text_emotion": e["emotion"],
                "face_confidence": None,
                "text_confidence": e["confidence"],
                "resolution_reason": e["resolution_reason"],
                "journal_snippet": e["content"][:100],
                "clinical_tone": e["clinical_tone"],
            }
            for e in entries
        ]
