import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, Request, UploadFile

from .backends import InferenceBackend, create_backend
from .config import Settings
from .extraction import OutputParseError, parse_ktp
from .images import ALLOWED_CONTENT_TYPES, InvalidImageError, decode_image, limit_pixels
from .schemas import HealthResponse, KTPResponse

logger = logging.getLogger(__name__)


def create_app(settings: Settings) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        backend = create_backend(settings)
        await backend.start()
        app.state.backend = backend
        yield
        await backend.close()

    app = FastAPI(
        title="KTP OCR API",
        description="Extract structured data from Indonesian KTP cards using Qwen2.5-VL.",
        version="1.1.0",
        lifespan=lifespan,
    )
    app.state.settings = settings

    @app.post(
        "/extract/ktp",
        response_model=KTPResponse,
        summary="Extract KTP fields from an uploaded image",
        tags=["KTP OCR"],
    )
    async def extract_ktp(
        request: Request,
        file: UploadFile = File(..., description="KTP image file (jpg/png/webp)"),
    ) -> KTPResponse:
        backend: InferenceBackend = request.app.state.backend
        image = await _read_upload(file, settings)

        try:
            raw_output = await backend.generate(image)
            ktp_data = parse_ktp(raw_output)
        except OutputParseError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        except Exception as exc:
            logger.exception("Inference error")
            raise HTTPException(status_code=500, detail=f"Inference failed: {exc}")

        logger.info("Extraction complete: NIK=%s, NAMA=%s", ktp_data.NIK, ktp_data.NAMA)
        return KTPResponse(success=True, data=ktp_data, raw_output=raw_output)

    @app.get("/health", response_model=HealthResponse, tags=["System"])
    async def health(request: Request) -> HealthResponse:
        backend: InferenceBackend = request.app.state.backend
        ready = await backend.is_ready()
        return HealthResponse(
            status="ok" if ready else "degraded",
            backend=backend.name,
            model_loaded=ready,
        )

    return app


async def _read_upload(file: UploadFile, settings: Settings):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{file.content_type}'. Use JPEG, PNG, or WebP.",
        )

    contents = await file.read()
    if len(contents) > settings.max_upload_bytes:
        max_mb = settings.max_upload_bytes // (1024 * 1024)
        raise HTTPException(status_code=413, detail=f"File too large (max {max_mb} MB).")

    logger.info("Running inference on file: %s (%d bytes)", file.filename, len(contents))
    try:
        image = await asyncio.to_thread(decode_image, contents)
    except InvalidImageError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return await asyncio.to_thread(limit_pixels, image, settings.max_pixels)
