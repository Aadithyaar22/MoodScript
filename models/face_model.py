import numpy as np
from PIL import Image
import io
import base64
from transformers import pipeline

LABEL_MAP = {
    "angry":    "angry",
    "disgust":  "disgusted",
    "fear":     "fearful",
    "happy":    "happy",
    "neutral":  "neutral",
    "sad":      "sad",
    "surprise": "surprised",
}
UNIFIED_EMOTIONS = ["angry", "disgusted", "fearful", "happy", "neutral", "sad", "surprised"]

class FaceEmotionModel:
    def __init__(self):
        print("Loading trpakov/vit-face-expression...")
        self.pipe = pipeline(
            "image-classification",
            model="trpakov/vit-face-expression",
            top_k=None,
            device=-1,
        )
        print("Face model ready.")

    def predict(self, image_base64: str) -> dict:
        if "," in image_base64:
            image_base64 = image_base64.split(",")[1]

        image_data = base64.b64decode(image_base64)
        image = Image.open(io.BytesIO(image_data)).convert("RGB")

        print(f"[FaceModel] Image size: {image.size}")

        results = self.pipe(image)
        print(f"[FaceModel] Raw results: {results}")

        conf_dict = {e: 0.0 for e in UNIFIED_EMOTIONS}
        for r in results:
            unified = LABEL_MAP.get(r["label"].lower(), "neutral")
            conf_dict[unified] += r["score"]

        total = sum(conf_dict.values())
        if total > 0:
            conf_dict = {k: v / total for k, v in conf_dict.items()}

        dominant = max(conf_dict, key=conf_dict.get)
        print(f"[FaceModel] Dominant: {dominant} ({conf_dict[dominant]:.2%})")

        return {
            "emotion": dominant,
            "confidence": conf_dict[dominant],
            "all_scores": conf_dict,
        }
