FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu \
    && python -c "import torch, torchvision; print('torch OK', torch.__version__, torchvision.__version__)" \
    && pip install --no-cache-dir -r requirements.txt \
    && python -c "import torch, torchvision; print('torch OK after full install', torch.__version__, torchvision.__version__)" \
    && python -c "from transformers import pipeline; print('transformers pipeline OK')" \
    && python -m spacy download en_core_web_sm

COPY . .

ENV HF_HOME=/app/.cache/huggingface
RUN mkdir -p /app/.cache/huggingface && chmod -R 777 /app

EXPOSE 7860

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
