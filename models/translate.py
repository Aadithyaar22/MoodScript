import os
import json
from google.cloud import translate_v2 as translate
from google.oauth2 import service_account

_client = None

def _get_client():
    global _client
    if _client is not None:
        return _client
    creds_json = os.getenv("GOOGLE_TRANSLATE_CREDENTIALS")
    if creds_json:
        info = json.loads(creds_json)
        credentials = service_account.Credentials.from_service_account_info(info)
        _client = translate.Client(credentials=credentials)
    else:
        _client = translate.Client()
    return _client

def translate_text(text: str, target_language: str) -> str:
    """Translate text into target_language (ISO 639-1, e.g. 'en', 'hi', 'kn')."""
    if not text or not text.strip():
        return text
    try:
        client = _get_client()
        result = client.translate(text, target_language=target_language, format_="text")
        return result["translatedText"]
    except Exception as e:
        print(f"[translate] ERROR: {type(e).__name__}: {e}")
        return text
