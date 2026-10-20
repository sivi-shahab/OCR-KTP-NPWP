import asyncio
import logging
from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.openapi.docs import get_swagger_ui_html, get_swagger_ui_oauth2_redirect_html
from fastapi.staticfiles import StaticFiles
from PIL import Image

from .backends import InferenceBackend, create_backend
from .config import Settings
from .documents import DOCUMENTS, DocumentType
from .extraction import OutputParseError, parse_fields
from .images import ALLOWED_CONTENT_TYPES, InvalidImageError, decode_image, limit_pixels
from .schemas import HealthResponse

logger = logging.getLogger(__name__)

# Swagger UI (swagger-ui-dist 5.17.14) is served from here instead of FastAPI's default
# CDN, so /docs also works for clients without internet access.
SWAGGER_UI_DIR = Path(__file__).parent / "static" / "swagger-ui"


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
                    "(KTP, NPWP) using Qwen2.5-VL.",
        version="2.0.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
    )
    app.state.settings = settings
    _add_docs_routes(app)

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
    async def extract(
        request: Request,
        file: UploadFile = File(..., description=f"{document.label} image file (jpg/png/webp)"),
    ):
        backend: InferenceBackend = request.app.state.backend
        image = await _read_upload(file, settings)

        try:
            raw_output = await backend.generate(image, document.prompt, document.json_schema)
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

    app.add_api_route(
        f"/extract/{document.key}",
        extract,
        methods=["POST"],
        response_model=document.response_model,
        summary=f"Extract {document.label} fields from an uploaded image",
        tags=[f"{document.label} OCR"],
        name=f"extract_{document.key}",
    )


async def _read_upload(file: UploadFile, settings: Settings) -> Image.Image:
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
