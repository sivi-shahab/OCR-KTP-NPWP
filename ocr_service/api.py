import asyncio
import base64
import binascii
import logging
import secrets
from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, Request, Security, UploadFile
from fastapi.openapi.docs import get_swagger_ui_html, get_swagger_ui_oauth2_redirect_html
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles
from PIL import Image

from .backends import InferenceBackend, create_backend
from .config import Settings
from .documents import DOCUMENTS, DocumentType
from .extraction import OutputParseError, parse_fields
from .images import ALLOWED_CONTENT_TYPES, InvalidImageError, decode_image, limit_pixels
from .schemas import Base64ImageRequest, HealthResponse

logger = logging.getLogger(__name__)

# Swagger UI (swagger-ui-dist 5.17.14) is served from here instead of FastAPI's default
# CDN, so /docs also works for clients without internet access.
SWAGGER_UI_DIR = Path(__file__).parent / "static" / "swagger-ui"

# auto_error=False so a missing header returns our 401 instead of FastAPI's 403.
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _api_key_dependency(settings: Settings):
    async def verify_api_key(api_key: str | None = Security(api_key_header)) -> None:
        if not settings.api_keys:
            return
        if not api_key or not any(secrets.compare_digest(api_key, key) for key in settings.api_keys):
            raise HTTPException(
                status_code=401,
                detail="Missing or invalid X-API-Key header.",
                headers={"WWW-Authenticate": "ApiKey"},
            )

    return verify_api_key


def create_app(settings: Settings) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        backend = create_backend(settings)
        await backend.start()
        app.state.backend = backend
        yield
        await backend.close()

    app = FastAPI(
        title="OCR API",
        description="Extract structured data from Indonesian identity documents "
                    "(KTP, NPWP, Kartu Keluarga) using Qwen2.5-VL.",
        version="2.0.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
    )
    app.state.settings = settings
    _add_docs_routes(app)

    if not settings.api_keys:
        logger.warning("API_KEYS is not set: /extract/* endpoints are open without authentication")
    for document in DOCUMENTS:
        _add_extract_route(app, document, settings)

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


def _add_docs_routes(app: FastAPI) -> None:
    app.mount("/static/swagger-ui", StaticFiles(directory=SWAGGER_UI_DIR), name="swagger-ui")

    @app.get("/docs", include_in_schema=False)
    async def swagger_ui():
        return get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=f"{app.title} - Swagger UI",
            oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
            swagger_js_url="/static/swagger-ui/swagger-ui-bundle.js",
            swagger_css_url="/static/swagger-ui/swagger-ui.css",
            swagger_favicon_url="/static/swagger-ui/favicon-32x32.png",
        )

    @app.get(app.swagger_ui_oauth2_redirect_url, include_in_schema=False)
    async def swagger_ui_redirect():
        return get_swagger_ui_oauth2_redirect_html()


def _add_extract_route(app: FastAPI, document: DocumentType, settings: Settings) -> None:
    dependencies = [Depends(_api_key_dependency(settings))]
    max_pixels = document.max_pixels or settings.max_pixels
    max_new_tokens = document.max_new_tokens or settings.max_new_tokens

    async def run(request: Request, image: Image.Image):
        backend: InferenceBackend = request.app.state.backend
        try:
            raw_output = await backend.generate(
                image, document.prompt, document.json_schema, max_new_tokens
            )
            data = parse_fields(raw_output, document.data_model)
        except OutputParseError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        except Exception as exc:
            logger.exception("Inference error (%s)", document.key)
            raise HTTPException(status_code=500, detail=f"Inference failed: {exc}")

        logger.info(
            "%s extraction complete: %s",
            document.label,
            ", ".join(f"{name}={getattr(data, name)}" for name in document.log_fields),
        )
        return document.response_model(success=True, data=data, raw_output=raw_output)

    async def extract(
        request: Request,
        # Swagger UI 5.17 only renders a file picker for `format: binary`; FastAPI's
        # OpenAPI 3.1 output uses `contentMediaType` instead, so add it explicitly.
        file: UploadFile = File(
            ...,
            description=f"{document.label} image file (jpg/png/webp)",
            json_schema_extra={"format": "binary"},
        ),
    ):
        return await run(request, await _read_upload(file, settings, max_pixels))

    async def extract_base64(request: Request, body: Base64ImageRequest):
        return await run(request, await _read_base64(body.image, settings, max_pixels))

    app.add_api_route(
        f"/extract/{document.key}",
        extract,
        methods=["POST"],
        response_model=document.response_model,
        summary=f"Extract {document.label} fields from an uploaded image",
        tags=[f"{document.label} OCR"],
        name=f"extract_{document.key}",
        dependencies=dependencies,
    )
    app.add_api_route(
        f"/extract/{document.key}/base64",
        extract_base64,
        methods=["POST"],
        response_model=document.response_model,
        summary=f"Extract {document.label} fields from a base64-encoded image (JSON body)",
        tags=[f"{document.label} OCR"],
        name=f"extract_{document.key}_base64",
        dependencies=dependencies,
    )


async def _read_upload(file: UploadFile, settings: Settings, max_pixels: int) -> Image.Image:
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
    return await asyncio.to_thread(limit_pixels, image, max_pixels)


async def _read_base64(encoded: str, settings: Settings, max_pixels: int) -> Image.Image:
    # Accept both a bare base64 string and a data URI ("data:image/jpeg;base64,...").
    if encoded.startswith("data:"):
        _, _, encoded = encoded.partition(",")
    encoded = "".join(encoded.split())

    max_mb = settings.max_upload_bytes // (1024 * 1024)
    if len(encoded) * 3 // 4 > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail=f"Image too large (max {max_mb} MB).")
    try:
        contents = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=400, detail="Field 'image' is not valid base64.")
    if len(contents) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail=f"Image too large (max {max_mb} MB).")

    logger.info("Running inference on base64 image (%d bytes)", len(contents))
    try:
        image = await asyncio.to_thread(decode_image, contents)
    except InvalidImageError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return await asyncio.to_thread(limit_pixels, image, max_pixels)
