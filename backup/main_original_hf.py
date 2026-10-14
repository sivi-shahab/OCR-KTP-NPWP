import json
import logging
import os
import re
import torch
from contextlib import asynccontextmanager
from io import BytesIO

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


PROMPT = """You are an OCR system specialized in Indonesian KTP (identity card) extraction.
Extract ALL text fields from this KTP image carefully and accurately.

Return ONLY valid JSON with this exact structure Output must start with '{' and end with '}'. 
Do not include any text before or after the JSON block (no markdown, no explanation):
{
    "NIK": "",
    "NAMA": "",
    "TTL": "",
    "JENIS_KELAMIN": "",
    "GOL_DARAH": "",
    "ALAMAT": "",
    "RT_RW": "",
    "KEL_DESA": "",
    "KECAMATAN": "",
    "AGAMA": "",
    "STATUS_PERKAWINAN": "",
    "PEKERJAAN": "",
    "KEWARGANEGARAAN": "",
    "BERLAKU_HINGGA": ""
}"""

# ---------------------------------------------------------------------------
# Global model state
# ---------------------------------------------------------------------------
model_state: dict = {}


# ---------------------------------------------------------------------------
# Lifespan — load model once at startup
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Use local directory if it already contains a downloaded model,
    # otherwise download from HuggingFace and save locally.
    if os.path.isdir(MODEL_LOCAL_DIR) and os.listdir(MODEL_LOCAL_DIR):
        logger.info("Loading model from local directory: %s", MODEL_LOCAL_DIR)
        load_path = MODEL_LOCAL_DIR
    else:
        logger.info("Local model not found. Downloading from HuggingFace: %s", MODEL_ID)
        load_path = MODEL_ID

    processor = AutoProcessor.from_pretrained(load_path)
    model = AutoModelForImageTextToText.from_pretrained(
        load_path,
        torch_dtype=torch.float16,
        device_map="auto",
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
# def parse_json_from_output(text: str) -> dict:
#     """Robustly extract JSON object from model output."""
#     text = re.sub(r"```(?:json)?", "", text).strip()
#     try:
#         return json.loads(text)
#     except json.JSONDecodeError:
#         pass
#     match = re.search(r"\{.*\}", text, re.DOTALL)
#     if match:
#         try:
#             return json.loads(match.group())
#         except json.JSONDecodeError:
#             pass
#     raise ValueError(f"Could not parse JSON from model output:\n{text}")

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


def run_inference(image: Image.Image) -> tuple[dict, str]:
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
        outputs = model.generate(**inputs, max_new_tokens=MAX_NEW_TOKENS)

    raw = processor.decode(
        outputs[0][inputs["input_ids"].shape[-1]:],
        skip_special_tokens=True,
    ).strip()

    parsed = parse_json_from_output(raw)
    return parsed, raw

# ---------------------------------------------------------------------------
# Endpoint (FIXED)
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
        image = Image.open(BytesIO(contents)).convert("RGB")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to read image: {exc}")

    logger.info("Running inference on file: %s (%d bytes)", file.filename, len(contents))

    try:
        parsed, raw_output = run_inference(image)
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
    
    # FIXED: Use NAMA (all caps) to match the class definition
    logger.info("Extraction complete: NIK=%s, NAMA=%s", ktp_data.NIK, ktp_data.NAMA)

    return KTPResponse(success=True, data=ktp_data, raw_output=raw_output)
# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------
# @app.post(
#     "/extract/ktp",
#     response_model=KTPResponse,
#     summary="Extract KTP fields from an uploaded image",
#     tags=["KTP OCR"],
# )
# async def extract_ktp(file: UploadFile = File(..., description="KTP image file (jpg/png/webp)")):
#     if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
#         raise HTTPException(
#             status_code=415,
#             detail=f"Unsupported file type '{file.content_type}'. Use JPEG, PNG, or WebP.",
#         )

#     try:
#         contents = await file.read()
#         image = Image.open(BytesIO(contents)).convert("RGB")
#     except Exception as exc:
#         raise HTTPException(status_code=400, detail=f"Failed to read image: {exc}")

#     logger.info("Running inference on file: %s (%d bytes)", file.filename, len(contents))

#     try:
#         parsed, raw_output = run_inference(image)
#     except ValueError as exc:
#         raise HTTPException(status_code=422, detail=str(exc))
#     except Exception as exc:
#         logger.exception("Inference error")
#         raise HTTPException(status_code=500, detail=f"Inference failed: {exc}")

#     ktp_data = KTPData(**{k: str(v) for k, v in parsed.items() if k in KTPData.model_fields})
#     logger.info("Extraction complete: NIK=%s, Nama=%s", ktp_data.NIK, ktp_data.Nama)

#     return KTPResponse(success=True, data=ktp_data, raw_output=raw_output)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health", tags=["System"])
async def health():
    return {"status": "ok", "model_loaded": bool(model_state)}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8070, reload=False)
