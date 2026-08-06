import os
import httpx
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, HTTPException, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List

from models.fusion import FusionLayer
from models.response import ResponseEngine
from models.crisis import assess_crisis
from models.rating import compute_rating, summarize_history
from models.translate import translate_text, translate_texts
from database.db import MoodDatabase
from auth import get_current_user_id, hash_password, verify_password, create_token
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
FACE_SERVICE_URL = os.getenv("FACE_SERVICE_URL", "http://localhost:8001")
TEXT_SERVICE_URL = os.getenv("TEXT_SERVICE_URL", "http://localhost:8002")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY")

def _internal_headers():
    return {"X-Internal-Key": INTERNAL_API_KEY} if INTERNAL_API_KEY else {}

app = FastAPI(title="MoodScript API")

_extra_origins = [o.strip() for o in os.getenv("CORS_EXTRA_ORIGINS", "").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", *_extra_origins],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

fusion = None
response_engine = None
db = None

@app.on_event("startup")
async def startup_event():
    global fusion, response_engine, db
    fusion = FusionLayer()
    response_engine = ResponseEngine()
    db = MoodDatabase()
    print("Orchestrator ready. Face service:", FACE_SERVICE_URL, "| Text service:", TEXT_SERVICE_URL)

_SERVICE_TIMEOUT = httpx.Timeout(75.0, connect=15.0)

async def _analyze_message(text: str, image_base64: Optional[str]):
    async with httpx.AsyncClient(timeout=_SERVICE_TIMEOUT) as client:
        try:
            text_resp = await client.post(
                f"{TEXT_SERVICE_URL}/analyze", json={"text": text}, headers=_internal_headers(),
            )
            text_resp.raise_for_status()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Text analysis service unavailable: {e}")
        text_data = text_resp.json()
        text_result = text_data["text_result"]
        xai_result = text_data["xai_result"]

        face_result = None
        if image_base64:
            try:
                face_resp = await client.post(
                    f"{FACE_SERVICE_URL}/predict", json={"image_base64": image_base64}, headers=_internal_headers(),
                )
                face_resp.raise_for_status()
                face_result = face_resp.json()
            except Exception as e:
                print(f"[FACE ERROR] {type(e).__name__}: {e}")

    fusion_result = fusion.fuse(text_result, face_result)

    return text_result, face_result, fusion_result, xai_result

# ---------- auth ----------

class SignupRequest(BaseModel):
    username: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/auth/signup")
async def signup(req: SignupRequest):
    username = req.username.strip()
    if not username or len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Username required and password must be at least 6 characters")
    if db.get_user_by_username(username):
        raise HTTPException(status_code=409, detail="Username already taken")

    user_id = db.create_user(username, hash_password(req.password))
    token = create_token(user_id, username)
    return {"token": token, "user_id": user_id, "username": username}

@app.post("/auth/login")
async def login(req: LoginRequest):
    user = db.get_user_by_username(req.username.strip())
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_token(user["id"], user["username"])
    return {"token": token, "user_id": user["id"], "username": user["username"]}

class GoogleAuthRequest(BaseModel):
    credential: str

@app.post("/auth/google")
async def auth_google(req: GoogleAuthRequest):
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured yet")
    try:
        idinfo = google_id_token.verify_oauth2_token(req.credential, google_requests.Request(), GOOGLE_CLIENT_ID)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Google credential")

    google_uid = idinfo["sub"]
    email = idinfo.get("email")

    user = db.get_user_by_google_id(google_uid)
    if not user:
        existing = db.get_user_by_username(email)
        if existing:
            db.link_google_id(existing["id"], google_uid)
            user = existing
        else:
            user_id = db.create_user(email, password_hash=None, google_id=google_uid)
            user = {"id": user_id, "username": email}

    token = create_token(user["id"], user["username"])
    return {"token": token, "user_id": user["id"], "username": user["username"]}

@app.get("/auth/me")
async def me(user_id: int = Depends(get_current_user_id)):
    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user_id": user["id"], "username": user["username"]}

# ---------- chat ----------

class ChatRequest(BaseModel):
    message: str
    image_base64: Optional[str] = None
    conversation_id: Optional[int] = None
    lang: Optional[str] = "en"

@app.post("/chat")
async def chat(req: ChatRequest, user_id: int = Depends(get_current_user_id)):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    lang = req.lang or "en"
    message_en = translate_text(req.message, "en") if lang != "en" else req.message

    if req.conversation_id is None:
        conversation_id = db.create_conversation(user_id, persona_id=None)
        prior_messages = []
    else:
        conversation = db.get_conversation(req.conversation_id, user_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        conversation_id = conversation["id"]
        prior_messages = db.get_conversation_messages(conversation_id, user_id)

    text_result, face_result, fusion_result, xai_result = await _analyze_message(message_en, req.image_base64)
    emotion = fusion_result["unified_emotion"]
    confidence = fusion_result["unified_confidence"]
    clinical_tone = text_result.get("clinical_tone")
    resolution_reason = fusion_result.get("resolution_reason", "text_only")

    journal_entries = db.get_user_journal_entries(user_id, exclude_conversation_id=conversation_id)
    crisis = assess_crisis(message_en, journal_entries)

    db.add_message(
        conversation_id, user_id, role="user", content=message_en,
        emotion=emotion, confidence=confidence,
        face_emotion=face_result["emotion"] if face_result else None,
        clinical_tone=clinical_tone, resolution_reason=resolution_reason,
        crisis_flag=crisis["is_crisis"],
    )

    conversation_row = db.get_conversation(conversation_id, user_id)
    persona_id = conversation_row["persona_id"]
    history_for_llm = [{"role": m["role"], "content": m["content"]} for m in prior_messages]
    long_term_context = summarize_history(journal_entries)

    if crisis["is_crisis"]:
        if persona_id is None:
            persona_id = 0
        response = await response_engine.generate_crisis_reply(
            reason=crisis["reason"], user_text=message_en,
            history=history_for_llm, persona_id=persona_id,
        )
    elif not prior_messages:
        response, persona_id = await response_engine.generate(
            emotion=emotion, confidence=confidence, user_text=message_en,
            clinical_tone=clinical_tone, conflict_note=resolution_reason,
            persona_id=persona_id, long_term_context=long_term_context,
        )
    else:
        response = await response_engine.generate_reply(
            history=history_for_llm, emotion=emotion, confidence=confidence,
            user_text=message_en, clinical_tone=clinical_tone,
            persona_id=persona_id, long_term_context=long_term_context,
        )

    if conversation_row["persona_id"] is None:
        db.set_conversation_persona(conversation_id, persona_id)

    db.add_message(conversation_id, user_id, role="assistant", content=response, crisis_flag=crisis["is_crisis"])

    display_response = translate_text(response, lang) if lang != "en" else response

    overall_rating = compute_rating(db.get_user_journal_entries(user_id))

    return {
        "conversation_id": conversation_id,
        "unified_emotion": emotion,
        "unified_confidence": confidence,
        "text_result": text_result,
        "face_result": face_result,
        "fusion_result": fusion_result,
        "xai": xai_result,
        "response": display_response,
        "emotion_arc": text_result.get("emotion_arc", []),
        "persona_id": persona_id,
        "crisis": crisis,
        "rating": overall_rating,
    }

class TranslateBatchRequest(BaseModel):
    texts: List[str]
    target: str

@app.post("/translate")
async def translate_batch(req: TranslateBatchRequest, user_id: int = Depends(get_current_user_id)):
    if req.target == "en" or not req.texts:
        return {"translated": req.texts}
    return {"translated": translate_texts(req.texts, req.target)}

# ---------- conversations ----------

@app.get("/conversations")
async def conversations(user_id: int = Depends(get_current_user_id)):
    return db.list_conversations(user_id)

@app.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: int, user_id: int = Depends(get_current_user_id)):
    conversation = db.get_conversation(conversation_id, user_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    db.delete_conversation(conversation_id, user_id)
    return {"deleted": True}

@app.get("/conversations/{conversation_id}/messages")
async def conversation_messages(conversation_id: int, user_id: int = Depends(get_current_user_id)):
    conversation = db.get_conversation(conversation_id, user_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return db.get_conversation_messages(conversation_id, user_id)

# ---------- history & rating ----------

@app.get("/history")
async def history(user_id: int = Depends(get_current_user_id)):
    return db.get_history(user_id, limit=30)

@app.get("/rating")
async def rating(user_id: int = Depends(get_current_user_id)):
    return compute_rating(db.get_user_journal_entries(user_id))

# ---------- weekly reflection ----------

@app.get("/reflection")
async def reflection(user_id: int = Depends(get_current_user_id)):
    now = datetime.now(timezone.utc)
    week_key = now.strftime("%G-W%V")

    cached = db.get_reflection(user_id, week_key)
    if cached:
        return {"week_key": week_key, "content": cached["content"], "entry_count": cached["entry_count"], "cached": True}

    all_entries = db.get_user_journal_entries(user_id)
    cutoff = now - timedelta(days=7)
    week_entries = [e for e in all_entries if datetime.fromisoformat(e["created_at"]) >= cutoff]

    if not week_entries:
        return {"week_key": week_key, "content": None, "entry_count": 0, "cached": False}

    conversations = db.list_conversations(user_id, limit=1)
    persona_id = conversations[0]["persona_id"] if conversations else 0
    week_rating = compute_rating(week_entries)

    content = await response_engine.generate_reflection(week_entries, week_rating, persona_id)
    db.save_reflection(user_id, week_key, content, len(week_entries))
    return {"week_key": week_key, "content": content, "entry_count": len(week_entries), "cached": False}

# ---------- export & account ----------

@app.get("/export")
async def export_journal(user_id: int = Depends(get_current_user_id)):
    user = db.get_user_by_id(user_id)
    conversations = db.list_conversations(user_id, limit=1000)

    lines = [f"MoodScript journal export — {user['username']}", f"Generated: {datetime.now(timezone.utc).isoformat()}", ""]
    for conv in reversed(conversations):
        messages = db.get_conversation_messages(conv["id"], user_id)
        if not messages:
            continue
        lines.append("=" * 60)
        lines.append(f"Conversation started {conv['started_at']}")
        lines.append("=" * 60)
        for m in messages:
            speaker = "You" if m["role"] == "user" else "Aria"
            tag = f" [{m['emotion']}]" if m.get("emotion") else ""
            lines.append(f"\n{speaker}{tag}:\n{m['content']}")
        lines.append("")

    body = "\n".join(lines)
    return Response(
        content=body,
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename=moodscript_journal_{user['username']}.txt"},
    )

@app.delete("/account")
async def delete_account(user_id: int = Depends(get_current_user_id)):
    db.delete_user_data(user_id)
    return {"deleted": True}

@app.get("/health")
async def health():
    return {"status": "ok"}
