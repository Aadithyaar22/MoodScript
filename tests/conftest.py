"""Shared fixtures. The environment is pinned BEFORE `main` is imported: database/db.py builds
a Fernet at import time, and a dummy DATABASE_URL guarantees that if anything ever did try to
reach the real database the test would fail fast instead of touching Neon."""
import os
import sys

from cryptography.fernet import Fernet

os.environ["DATABASE_URL"] = "postgresql://nobody:nothing@127.0.0.1:1/never"
os.environ["MESSAGE_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
os.environ["JWT_SECRET"] = "test-secret-not-used-anywhere-real"
for _k in ("GROQ_API_KEY", "JAMENDO_CLIENT_ID", "GOOGLE_TRANSLATE_CREDENTIALS", "ANTHROPIC_API_KEY",
           "OPENAI_API_KEY"):
    os.environ[_k] = ""      # .env must not leak real credentials into tests
for _k in ("MOODSCRIPT_LEGACY_FUSION", "MOODSCRIPT_ENABLE_ARBITER", "MOODSCRIPT_FUSION",
           "INTERNAL_API_KEY", "GOOGLE_CLIENT_ID"):
    os.environ.pop(_k, None)

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import httpx          # noqa: E402
import pytest         # noqa: E402
from fastapi.testclient import TestClient   # noqa: E402

import main           # noqa: E402
from models.fusion import FusionLayer       # noqa: E402
from fakes import FakeDB, FakeResponseEngine, StubServices   # noqa: E402


@pytest.fixture
def fake_db():
    return FakeDB()


@pytest.fixture
def engine():
    return FakeResponseEngine()


@pytest.fixture
def stub():
    return StubServices()


@pytest.fixture
def client(monkeypatch, fake_db, engine, stub):
    """The real FastAPI app with its collaborators swapped for in-memory fakes. TestClient is
    used without a `with` block on purpose so the real startup hook (which would open the
    database and the LLM client) never runs."""
    real_async_client = httpx.AsyncClient

    class _Stubbed(real_async_client):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = httpx.MockTransport(stub.handler)
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", _Stubbed)
    monkeypatch.setattr(main, "db", fake_db)
    monkeypatch.setattr(main, "fusion", FusionLayer())
    monkeypatch.setattr(main, "arbiter", None)
    monkeypatch.setattr(main, "ARBITER_ENABLED", False)
    monkeypatch.setattr(main, "response_engine", engine)
    # translation is an external Google call: replace it with a visible marker
    monkeypatch.setattr(main, "translate_text", lambda text, lang: f"[{lang}] {text}")
    monkeypatch.setattr(main, "translate_texts", lambda texts, lang: [f"[{lang}] {t}" for t in texts])
    return TestClient(main.app)


def signup(client, username="alice", password="secret123"):
    r = client.post("/auth/signup", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture
def auth(client):
    """Headers for a freshly signed-up user, plus their id."""
    data = signup(client)
    return {"Authorization": f"Bearer {data['token']}"}, data["user_id"]


@pytest.fixture
def headers(auth):
    return auth[0]


# Browser tests need Playwright (see requirements-e2e.txt); without it they are skipped, not failed.
try:
    import playwright  # noqa: F401
except ImportError:
    collect_ignore = ["e2e"]
