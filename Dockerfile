# OCR API (KTP & NPWP) — lightweight image for INFERENCE_BACKEND=vllm.
# No torch/transformers inside: inference runs in the separate vLLM container (see docker-compose.yml).
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY main.py .
COPY ocr_service/ ocr_service/

RUN useradd --system --uid 10001 --no-create-home app
USER app

ENV INFERENCE_BACKEND=vllm \
    HOST=0.0.0.0 \
    PORT=8000 \
    VLLM_URL=http://vllm:8071

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import json,os,urllib.request; r=urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/health', timeout=4); exit(0 if json.load(r)['status']=='ok' else 1)"

CMD ["python", "main.py"]
