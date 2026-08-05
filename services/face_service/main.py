import os
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from face_model import FaceEmotionModel

INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY")

app = FastAPI(title="MoodScript Face Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

face_model = None

@app.on_event("startup")
async def startup_event():
    global face_model
    print("Loading face model...")
    face_model = FaceEmotionModel()
    print("Face service ready.")

def _check_key(x_internal_key: str = Header(None)):
    if INTERNAL_API_KEY and x_internal_key != INTERNAL_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing internal API key")

class PredictRequest(BaseModel):
    image_base64: str

@app.post("/predict")
async def predict(req: PredictRequest, x_internal_key: str = Header(None)):
    _check_key(x_internal_key)
    return face_model.predict(req.image_base64)

@app.get("/health")
async def health():
    return {"status": "ok"}
