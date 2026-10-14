"""Entry point: `python main.py` or `uvicorn main:app`.

Set INFERENCE_BACKEND=vllm to use the vLLM server started by run_vllm.sh.
"""

import logging

from ocr_service.api import create_app
from ocr_service.config import Settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

settings = Settings.from_env()
app = create_app(settings)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port)
