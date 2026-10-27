import asyncio
import base64
import logging
from io import BytesIO

import httpx
from PIL import Image

from ..config import Settings
from .base import InferenceBackend

logger = logging.getLogger(__name__)

class VLLMBackend(InferenceBackend):
    """Calls a separate `vllm serve` instance through its OpenAI-compatible API."""

    name = "vllm"

    def __init__(self, settings: Settings):
        self._settings = settings
        self._client = httpx.AsyncClient(base_url=settings.vllm_url, timeout=settings.vllm_timeout)

    async def start(self) -> None:
        if await self.is_ready():
            logger.info("Using vLLM backend at %s", self._settings.vllm_url)
        else:
            logger.warning("vLLM backend at %s not reachable yet", self._settings.vllm_url)

    async def close(self) -> None:
        await self._client.aclose()

    async def is_ready(self) -> bool:
        try:
            return (await self._client.get("/health")).is_success
        except httpx.HTTPError:
            return False

    async def generate(
        self, image: Image.Image, prompt: str, json_schema: dict, max_new_tokens: int
    ) -> str:
        image_url = await asyncio.to_thread(_to_data_url, image)
        payload = {
            "model": self._settings.vllm_model,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": image_url}},
                    {"type": "text", "text": prompt},
                ],
            }],
            "max_tokens": max_new_tokens,
            "temperature": 0,
            "repetition_penalty": 1.0,
            # Structured output: vLLM constrains decoding to the schema, so the JSON is always valid
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": json_schema.get("title", "document"), "schema": json_schema},
            },
        }
        response = await self._client.post("/v1/chat/completions", json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()


def _to_data_url(image: Image.Image) -> str:
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=95)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode()
