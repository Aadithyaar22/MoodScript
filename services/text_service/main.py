import os
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from text_model import TextEmotionModel
from explainer import XAIExplainer

INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY")

app = FastAPI(title="MoodScript Text Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

text_model = None
xai = None

@app.on_event("startup")
async def startup_event():
    global text_model, xai
    print("Loading text model...")
    text_model = TextEmotionModel()
    xai = XAIExplainer(text_model)
    print("Text service ready.")

def _check_key(x_internal_key: str = Header(None)):
    if INTERNAL_API_KEY and x_internal_key != INTERNAL_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing internal API key")

class AnalyzeRequest(BaseModel):
    text: str

@app.post("/analyze")
async def analyze(req: AnalyzeRequest, x_internal_key: str = Header(None)):
    _check_key(x_internal_key)
    text_result = text_model.predict(req.text)
    xai_result = xai.explain(req.text, text_result)
    return {"text_result": text_result, "xai_result": xai_result}

@app.get("/health")
async def health():
    return {"status": "ok"}
