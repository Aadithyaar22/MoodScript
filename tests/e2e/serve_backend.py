"""The REAL orchestrator (main.app) with its collaborators replaced by the in-memory fakes from
tests/fakes.py, served over HTTP for the browser tests. No Neon, no Groq, no model services.

Test-only control endpoints (/__test/*) are added to the app here, in this process only; they
do not exist in the production code. The browser tests use them to reset state and to make the
fake model services fail on demand."""
import os
import sys

from cryptography.fernet import Fernet

PORT = int(os.environ.get("E2E_BACKEND_PORT", "8765"))
FRONTEND_PORT = int(os.environ.get("E2E_FRONTEND_PORT", "5199"))

os.environ["DATABASE_URL"] = "postgresql://nobody:nothing@127.0.0.1:1/never"
os.environ["MESSAGE_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
os.environ["JWT_SECRET"] = "e2e-secret"
# .env (loaded by models/*.py) must not leak real credentials into a test process; load_dotenv
# never overrides a variable that is already set, even to an empty string.
for _k in ("GROQ_API_KEY", "JAMENDO_CLIENT_ID", "GOOGLE_TRANSLATE_CREDENTIALS", "GOOGLE_CLIENT_ID",
           "ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
    os.environ[_k] = ""
os.environ["CORS_EXTRA_ORIGINS"] = f"http://localhost:{FRONTEND_PORT},http://127.0.0.1:{FRONTEND_PORT}"
for k in ("MOODSCRIPT_LEGACY_FUSION", "MOODSCRIPT_ENABLE_ARBITER", "MOODSCRIPT_FUSION", "INTERNAL_API_KEY"):
    os.environ.pop(k, None)

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(HERE, ".."))

import httpx          # noqa: E402
import uvicorn        # noqa: E402

import main           # noqa: E402
from models.fusion import FusionLayer   # noqa: E402
from fakes import FakeDB, FakeResponseEngine, StubServices   # noqa: E402

state = {"stub": StubServices()}
_real_client = httpx.AsyncClient


class _Stubbed(_real_client):
    def __init__(self, *a, **kw):
        kw["transport"] = httpx.MockTransport(lambda req: state["stub"].handler(req))
        super().__init__(*a, **kw)


def reset():
    state["stub"] = StubServices()
    main.db = FakeDB()
    main.response_engine = FakeResponseEngine()


httpx.AsyncClient = _Stubbed
# The real startup hook opens the Neon connection pool and builds the Groq client. The fakes
# below replace both, so the hook must not run at all.
main.app.router.on_startup.clear()
main.fusion = FusionLayer()
main.arbiter = None
main.ARBITER_ENABLED = False
main.translate_text = lambda text, lang: f"[{lang}] {text}"
main.translate_texts = lambda texts, lang: [f"[{lang}] {t}" for t in texts]
reset()


@main.app.post("/__test/reset")
async def _reset():
    reset()
    return {"ok": True}


@main.app.post("/__test/stub")
async def _stub(settings: dict):
    for k, v in settings.items():
        setattr(state["stub"], k, v)
    return {"ok": True}


@main.app.get("/__test/requests")
async def _requests():
    return [{"path": p, "has_text": "text" in b, "has_image": "image_base64" in b}
            for p, b in state["stub"].requests]


if __name__ == "__main__":
    uvicorn.run(main.app, host="127.0.0.1", port=PORT, log_level="warning")
