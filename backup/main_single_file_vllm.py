import asyncio
import base64
import json
import logging
import os
import re
import torch
from contextlib import asynccontextmanager
from io import BytesIO

import httpx
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image
from pydantic import BaseModel
from transformers import AutoProcessor, AutoModelForImageTextToText

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MODEL_ID        = "Qwen/Qwen2.5-VL-3B-Instruct"
MODEL_LOCAL_DIR = "model/"
MAX_NEW_TOKENS  = 512
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

# Qwen2.5-VL default allows up to ~12.8M pixels (~16k visual tokens) per image.
# A KTP is readable at ~1M pixels; capping this is the single biggest speed win.
MIN_PIXELS = int(os.getenv("MIN_PIXELS", 256 * 28 * 28))
MAX_PIXELS = int(os.getenv("MAX_PIXELS", 1280 * 28 * 28))

# "hf"   = load the model in-process with transformers (default)
# "vllm" = call a separate `vllm serve` instance (see run_vllm.sh); much faster
#          and batches concurrent requests instead of serializing them
INFERENCE_BACKEND = os.getenv("INFERENCE_BACKEND", "hf").lower()
VLLM_URL          = os.getenv("VLLM_URL", "http://127.0.0.1:8071")
VLLM_MODEL        = os.getenv("VLLM_MODEL", "qwen-ktp")
VLLM_TIMEOUT      = float(os.getenv("VLLM_TIMEOUT", 120))


PROMPT = """You are an OCR system specialized in Indonesian KTP (identity card) extraction.
Extract ALL text fields from this KTP image carefully and accurately.

Return ONLY valid JSON with exactly these keys, as compact JSON on a single line
(no indentation, no newlines, no markdown, no explanation). Use "" for unreadable fields:
{"NIK":"","NAMA":"","TTL":"","JENIS_KELAMIN":"","GOL_DARAH":"","ALAMAT":"","RT_RW":"","KEL_DESA":"","KECAMATAN":"","AGAMA":"","STATUS_PERKAWINAN":"","PEKERJAAN":"","KEWARGANEGARAAN":"","BERLAKU_HINGGA":""}"""

# ---------------------------------------------------------------------------
# Global model state
# ---------------------------------------------------------------------------
model_state: dict = {}


# ---------------------------------------------------------------------------
# Lifespan — load model once at startup
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    if INFERENCE_BACKEND == "vllm":
        client = httpx.AsyncClient(base_url=VLLM_URL, timeout=VLLM_TIMEOUT)
        try:
            (await client.get("/health")).raise_for_status()
            logger.info("Using vLLM backend at %s", VLLM_URL)
        except httpx.HTTPError as exc:
            logger.warning("vLLM backend at %s not reachable yet: %s", VLLM_URL, exc)
        model_state["client"] = client
        yield
        await client.aclose()
        model_state.clear()
        return

    # Use local directory if it already contains a downloaded model,
    # otherwise download from HuggingFace and save locally.
    if os.path.isdir(MODEL_LOCAL_DIR) and os.listdir(MODEL_LOCAL_DIR):
        logger.info("Loading model from local directory: %s", MODEL_LOCAL_DIR)
        load_path = MODEL_LOCAL_DIR
    else:
        logger.info("Local model not found. Downloading from HuggingFace: %s", MODEL_ID)
        load_path = MODEL_ID

    processor = AutoProcessor.from_pretrained(
        load_path,
        size={"shortest_edge": MIN_PIXELS, "longest_edge": MAX_PIXELS},
    )
    # bf16 is Qwen2.5-VL's native dtype; fp16 can overflow in the vision tower
    model = AutoModelForImageTextToText.from_pretrained(
        load_path,
        dtype=torch.bfloat16,
        device_map="auto",
        attn_implementation="sdpa",
    )

    # Save to local dir after first download so next startup is instant
    if load_path == MODEL_ID:
        logger.info("Saving model & processor to: %s", MODEL_LOCAL_DIR)
        os.makedirs(MODEL_LOCAL_DIR, exist_ok=True)
        processor.save_pretrained(MODEL_LOCAL_DIR)
        model.save_pretrained(MODEL_LOCAL_DIR)
        logger.info("Model saved successfully to %s", MODEL_LOCAL_DIR)

    model.eval()
    model_state["processor"] = processor
    model_state["model"] = model
    model_state["lock"] = asyncio.Lock()

    # Warm-up so the first real request doesn't pay CUDA init / kernel selection cost
    try:
        run_inference(Image.new("RGB", (856, 540), "white"), max_new_tokens=8, parse=False)
    except Exception:
        logger.exception("Warm-up failed (continuing)")

    logger.info("Model ready on device: %s", next(model.parameters()).device)
    yield
    model_state.clear()
    logger.info("Model unloaded.")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="KTP OCR API",
    description="Extract structured data from Indonesian KTP cards using Qwen2.5-VL.",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------    
class KTPData(BaseModel):
    NIK: str = ""
    NAMA: str = ""
    TTL: str = ""
    JENIS_KELAMIN: str = ""
    GOL_DARAH: str = ""
    ALAMAT: str = ""
    RT_RW: str = ""
    KEL_DESA: str = ""
    KECAMATAN: str = ""
    AGAMA: str = ""
    STATUS_PERKAWINAN: str = ""
    PEKERJAAN: str = ""
    KEWARGANEGARAAN: str = ""
    BERLAKU_HINGGA: str = ""

class KTPResponse(BaseModel):
    success: bool
    data: KTPData
    raw_output: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def parse_json_from_output(text: str) -> dict:
    # Find the outermost curly braces
    match = re.search(r"(\{.*\})", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in output: {text}")
    
    json_str = match.group(1)
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        # Fallback: simple cleanup for common LLM hiccups (like trailing commas)
        json_str = re.sub(r",\s*}", "}", json_str) 
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON: {e}\nRaw: {json_str}")


def run_inference(
    image: Image.Image, max_new_tokens: int = MAX_NEW_TOKENS, parse: bool = True
) -> tuple[dict, str]:
    processor = model_state["processor"]
    model     = model_state["model"]

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text",  "text": PROMPT},
            ],
        }
    ]

    inputs = processor.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    ).to(model.device)

    with torch.inference_mode():
        # Greedy decoding: deterministic and skips sampling overhead
        # (generation_config.json has do_sample=true, temperature=1e-6)
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            # Default config uses 1.05, which penalizes repeated digits (e.g. NIK "000")
            repetition_penalty=1.0,
            temperature=None,
            top_p=None,
            top_k=None,
        )

    raw = processor.decode(
        outputs[0][inputs["input_ids"].shape[-1]:],
        skip_special_tokens=True,
    ).strip()

    parsed = parse_json_from_output(raw) if parse else {}
    return parsed, raw

def encode_image(image: Image.Image) -> str:
    """Downscale to MAX_PIXELS and encode as a JPEG data URL (keeps the HTTP payload small)."""
    w, h = image.size
    if w * h > MAX_PIXELS:
        scale = (MAX_PIXELS / (w * h)) ** 0.5
        image = image.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    buf = BytesIO()
    image.save(buf, format="JPEG", quality=95)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


async def run_inference_vllm(image: Image.Image) -> tuple[dict, str]:
    data_url = await asyncio.to_thread(encode_image, image)
    payload = {
        "model": VLLM_MODEL,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": data_url}},
                {"type": "text", "text": PROMPT},
            ],
        }],
        "max_tokens": MAX_NEW_TOKENS,
        "temperature": 0,
        "repetition_penalty": 1.0,
        # Structured output: vLLM constrains decoding to this schema, so the JSON is always valid
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "ktp", "schema": KTPData.model_json_schema()},
        },
    }
    resp = await model_state["client"].post("/v1/chat/completions", json=payload)
    resp.raise_for_status()
    raw = resp.json()["choices"][0]["message"]["content"].strip()
    return parse_json_from_output(raw), raw


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------
@app.post(
    "/extract/ktp",
    response_model=KTPResponse,
    summary="Extract KTP fields from an uploaded image",
    tags=["KTP OCR"],
)
async def extract_ktp(file: UploadFile = File(..., description="KTP image file (jpg/png/webp)")):
    if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{file.content_type}'. Use JPEG, PNG, or WebP.",
        )

    try:
        contents = await file.read()
        if len(contents) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="File too large (max 10 MB).")
        image = Image.open(BytesIO(contents)).convert("RGB")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to read image: {exc}")

    logger.info("Running inference on file: %s (%d bytes)", file.filename, len(contents))

    try:
        if INFERENCE_BACKEND == "vllm":
            parsed, raw_output = await run_inference_vllm(image)
        else:
            # Run blocking GPU work off the event loop (keeps /health responsive),
            # one request at a time so concurrent uploads can't OOM the GPU.
            async with model_state["lock"]:
                parsed, raw_output = await asyncio.to_thread(run_inference, image)
    except ValueError as exc:
        # This handles the 422 if the model's JSON is unparseable
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.exception("Inference error")
        raise HTTPException(status_code=500, detail=f"Inference failed: {exc}")

    # Ensure keys match Pydantic model exactly (case-sensitive)
    # We also use .get() to avoid KeyErrors if the model skips a field
    clean_data = {
        field: str(parsed.get(field, "")) 
        for field in KTPData.model_fields
    }
    
    ktp_data = KTPData(**clean_data)
    
    logger.info("Extraction complete: NIK=%s, NAMA=%s", ktp_data.NIK, ktp_data.NAMA)

    return KTPResponse(success=True, data=ktp_data, raw_output=raw_output)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health", tags=["System"])
async def health():
    if INFERENCE_BACKEND == "vllm":
        try:
            ok = (await model_state["client"].get("/health")).is_success
        except (httpx.HTTPError, KeyError):
            ok = False
        return {"status": "ok" if ok else "degraded", "backend": "vllm", "model_loaded": ok}
    return {"status": "ok", "backend": "hf", "model_loaded": bool(model_state)}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8070, reload=False)
