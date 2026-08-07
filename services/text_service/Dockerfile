FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && python -c "import torch; print('torch OK', torch.__version__)" \
    && pip install --no-cache-dir -r requirements.txt \
    && python -m spacy download en_core_web_sm

ENV HF_HOME=/app/.cache/huggingface
RUN mkdir -p /app/.cache/huggingface && chmod -R 777 /app

# Bake the model weights into the image instead of downloading them at container
# startup — a cold start previously depended on HuggingFace Hub being reachable and
# not rate-limiting us, and a 429 there meant the service could never start at all.
RUN python -c "\
from transformers import pipeline; \
pipeline('text-classification', model='j-hartmann/emotion-english-distilroberta-base', top_k=None, device=-1); \
pipeline('text-classification', model='SamLowe/roberta-base-go_emotions', top_k=3, device=-1)"

# Weights are already baked in above — never touch the network for them again,
# even just for a metadata/update check.
ENV HF_HUB_OFFLINE=1

COPY . .

EXPOSE 8002

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
