import os
import json
from google.cloud import texttospeech
from google.oauth2 import service_account

_client = None

def _get_client():
    global _client
    if _client is not None:
        return _client
    creds_json = os.getenv("GOOGLE_TRANSLATE_CREDENTIALS")  # same GCP project/service account as Translate
    if creds_json:
        info = json.loads(creds_json)
        credentials = service_account.Credentials.from_service_account_info(info)
        _client = texttospeech.TextToSpeechClient(credentials=credentials)
    else:
        _client = texttospeech.TextToSpeechClient()
    return _client

# Neural2 is the highest-quality tier that still supports pitch/rate control (Chirp3-HD
# sounds even more natural but rejects pitch adjustments outright) — Kannada has no
# Neural2 voices yet, so it falls back to Wavenet, the next tier down.
VOICE_MAP = {
    "en": ("en-US", "en-US-Neural2-F"),
    "hi": ("hi-IN", "hi-IN-Neural2-A"),
    "kn": ("kn-IN", "kn-IN-Wavenet-A"),
}

# (speaking_rate, pitch_semitones) per detected emotion. Heuristic, not a benchmarked
# value — there's no ground truth for "correct" prosody, just a reasonable starting
# point for how a warm, attentive therapist's tone would shift.
EMOTION_PROSODY = {
    "happy":     (1.10,  3.0),
    "sad":       (0.88, -3.5),
    "angry":     (1.05, -1.5),
    "fearful":   (1.06,  1.5),
    "surprised": (1.05,  4.0),
    "disgusted": (0.95, -2.0),
    "neutral":   (1.00,  0.0),
}

def synthesize_speech(text: str, lang: str, emotion: str = "neutral") -> bytes:
    language_code, voice_name = VOICE_MAP.get(lang, VOICE_MAP["en"])
    rate, pitch = EMOTION_PROSODY.get(emotion, EMOTION_PROSODY["neutral"])

    client = _get_client()
    synth_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(language_code=language_code, name=voice_name)
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=rate,
        pitch=pitch,
    )
    response = client.synthesize_speech(input=synth_input, voice=voice, audio_config=audio_config)
    return response.audio_content
