import numpy as np
from PIL import Image
import io
import base64
from transformers import pipeline
import cv2

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
        print("Loading dima806/facial_emotions_image_detection...")
        self.pipe = pipeline(
            "image-classification",
            model="dima806/facial_emotions_image_detection",
            top_k=None,
            device=-1,
        )
        # The webcam sends a full 640x360 frame — background, off-center face,
        # arbitrary scale. Every FER model here (this one included) was trained and
        # benchmarked on tightly cropped, centered face images, so classifying the raw
        # frame directly is a real distribution mismatch, not a model-quality issue.
        # Detect and crop to the face first so the classifier sees what it expects.
        self._detector = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        print("Face model ready.")

    def _crop_to_face(self, image: Image.Image) -> Image.Image:
        gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
        faces = self._detector.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60),
        )
        if len(faces) == 0:
            print("[FaceModel] No face detected — using full frame")
            return image

        # Largest detected box is the primary subject (closest to camera).
        x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])
        w, h = image.size

        # Haar's box hugs eyes/nose/mouth — pad it out so the crop still
        # includes forehead-to-chin, matching what these models were trained on.
        margin_x, margin_y = int(fw * 0.35), int(fh * 0.45)
        x1 = max(0, x - margin_x)
        y1 = max(0, y - margin_y)
        x2 = min(w, x + fw + margin_x)
        y2 = min(h, y + fh + margin_y)

        if x2 <= x1 or y2 <= y1:
            return image
        print(f"[FaceModel] Face crop: ({x1},{y1})-({x2},{y2}) of {image.size}")
        return image.crop((x1, y1, x2, y2))

    def predict(self, image_base64: str) -> dict:
        if "," in image_base64:
            image_base64 = image_base64.split(",")[1]

        image_data = base64.b64decode(image_base64)
        image = Image.open(io.BytesIO(image_data)).convert("RGB")

        print(f"[FaceModel] Image size: {image.size}")
        image = self._crop_to_face(image)

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
