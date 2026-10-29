"""Entry point: `python main.py` or `uvicorn main:app`.

Uses the vLLM server started by run_vllm.sh by default; set INFERENCE_BACKEND=hf
to load the model in-process (needs requirements-hf.txt).
"""

import logging

from dotenv import load_dotenv

from ocr_service.api import create_app
from ocr_service.config import Settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

# Reads .env for local/screen runs. Variables already set in the environment (e.g. by
# Docker Compose) take precedence; the Docker image itself contains no .env.
load_dotenv()
settings = Settings.from_env()
app = create_app(settings)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port)
