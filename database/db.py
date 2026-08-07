import os
import psycopg2
import psycopg2.extras
import psycopg2.pool
from datetime import datetime, timezone
from cryptography.fernet import Fernet

DATABASE_URL = os.getenv("DATABASE_URL")
_fernet = Fernet(os.getenv("MESSAGE_ENCRYPTION_KEY"))

_pool = None

def _get_pool():
    global _pool
    if _pool is None:
        _pool = psycopg2.pool.ThreadedConnectionPool(
            1, 20, DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor,
        )
    return _pool

def _connect():
    """Borrow a connection from the pool, discarding it and getting a fresh one if
    Neon has silently closed it server-side while it sat idle — psycopg2's pool
    doesn't detect that on its own, so a stale connection would otherwise surface
    as an OperationalError on the caller's first query."""
    pool = _get_pool()
    conn = pool.getconn()
    if conn.closed:
        pool.putconn(conn, close=True)
        return pool.getconn()
    try:
        with conn.cursor() as c:
            c.execute("SELECT 1")
        conn.rollback()  # the ping opened a transaction — clear it before handing the connection off
    except psycopg2.Error:
        pool.putconn(conn, close=True)
        conn = pool.getconn()
    return conn

def _release(conn):
    """Return a connection to the pool instead of closing the socket outright —
    every db call used to pay a fresh TCP+TLS+auth handshake against Neon."""
    _get_pool().putconn(conn, close=conn.closed != 0)

def _now():
    return datetime.now(timezone.utc).isoformat()

def _encrypt(text: str) -> str:
    return _fernet.encrypt(text.encode()).decode()

def _decrypt(token: str):
    if token is None:
        return None
    return _fernet.decrypt(token.encode()).decode()

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
                password_hash TEXT,
                google_id TEXT UNIQUE,
                created_at TEXT NOT NULL
            )
        """)
        c.execute("ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS google_id TEXT UNIQUE")
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
        _release(conn)

    # ---------- users ----------
    def create_user(self, username: str, password_hash: str = None, google_id: str = None) -> int:
        conn = _connect()
        c = conn.cursor()
        c.execute(
            "INSERT INTO users (username, password_hash, google_id, created_at) VALUES (%s, %s, %s, %s) RETURNING id",
            (username, password_hash, google_id, _now()),
        )
        user_id = c.fetchone()["id"]
        conn.commit()
        _release(conn)
        return user_id

    def get_user_by_username(self, username: str):
        conn = _connect()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = %s", (username,))
        row = c.fetchone()
        _release(conn)
        return dict(row) if row else None

    def get_user_by_google_id(self, google_id: str):
        conn = _connect()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE google_id = %s", (google_id,))
        row = c.fetchone()
        _release(conn)
        return dict(row) if row else None

    def link_google_id(self, user_id: int, google_id: str):
        conn = _connect()
        c = conn.cursor()
        c.execute("UPDATE users SET google_id = %s WHERE id = %s", (google_id, user_id))
        conn.commit()
        _release(conn)

    def get_user_by_id(self, user_id: int):
        conn = _connect()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        row = c.fetchone()
        _release(conn)
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
        _release(conn)
        return conv_id

    def get_conversation(self, conversation_id: int, user_id: int):
        conn = _connect()
        c = conn.cursor()
        c.execute("SELECT * FROM conversations WHERE id = %s AND user_id = %s", (conversation_id, user_id))
        row = c.fetchone()
        _release(conn)
        return dict(row) if row else None

    def set_conversation_persona(self, conversation_id: int, persona_id: int):
        conn = _connect()
        c = conn.cursor()
        c.execute("UPDATE conversations SET persona_id = %s WHERE id = %s", (persona_id, conversation_id))
        conn.commit()
        _release(conn)

    def delete_conversation(self, conversation_id: int, user_id: int):
        conn = _connect()
        c = conn.cursor()
        c.execute("DELETE FROM messages WHERE conversation_id = %s AND user_id = %s", (conversation_id, user_id))
        c.execute("DELETE FROM conversations WHERE id = %s AND user_id = %s", (conversation_id, user_id))
        conn.commit()
        _release(conn)

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
        _release(conn)
        results = [dict(r) for r in rows]
        for r in results:
            r["opening_line"] = _decrypt(r["opening_line"])
        return results

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
        """, (conversation_id, user_id, role, _encrypt(content), emotion, confidence, face_emotion,
              clinical_tone, resolution_reason, int(crisis_flag), _now()))
        conn.commit()
        _release(conn)

    def get_conversation_messages(self, conversation_id: int, user_id: int):
        conn = _connect()
        c = conn.cursor()
        c.execute("""
            SELECT * FROM messages WHERE conversation_id = %s AND user_id = %s ORDER BY id ASC
        """, (conversation_id, user_id))
        rows = c.fetchall()
        _release(conn)
        results = [dict(r) for r in rows]
        for r in results:
            r["content"] = _decrypt(r["content"])
        return results

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
        _release(conn)
        results = [dict(r) for r in rows]
        for r in results:
            r["content"] = _decrypt(r["content"])
        return results

    # ---------- reflections ----------
    def get_reflection(self, user_id: int, week_key: str):
        conn = _connect()
        c = conn.cursor()
        c.execute("SELECT * FROM reflections WHERE user_id = %s AND week_key = %s", (user_id, week_key))
        row = c.fetchone()
        _release(conn)
        if not row:
            return None
        result = dict(row)
        result["content"] = _decrypt(result["content"])
        return result

    def save_reflection(self, user_id: int, week_key: str, content: str, entry_count: int):
        conn = _connect()
        c = conn.cursor()
        c.execute("""
            INSERT INTO reflections (user_id, week_key, content, entry_count, created_at)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (user_id, week_key) DO UPDATE SET content=excluded.content, entry_count=excluded.entry_count
        """, (user_id, week_key, _encrypt(content), entry_count, _now()))
        conn.commit()
        _release(conn)

    # ---------- account ----------
    def delete_user_data(self, user_id: int):
        conn = _connect()
        c = conn.cursor()
        c.execute("DELETE FROM messages WHERE user_id = %s", (user_id,))
        c.execute("DELETE FROM conversations WHERE user_id = %s", (user_id,))
        c.execute("DELETE FROM reflections WHERE user_id = %s", (user_id,))
        c.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        _release(conn)

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
