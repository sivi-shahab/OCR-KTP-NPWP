import asyncio
import logging
import os

import torch
from PIL import Image
from transformers import AutoModelForImageTextToText, AutoProcessor

from ..config import Settings
from .base import InferenceBackend

logger = logging.getLogger(__name__)


class HFBackend(InferenceBackend):
    """Runs Qwen2.5-VL in-process with transformers."""

    name = "hf"

    def __init__(self, settings: Settings):
        self._settings = settings
        self._processor = None
        self._model = None
        # One generation at a time so concurrent uploads can't OOM the GPU
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        await asyncio.to_thread(self._load)
        # Warm-up so the first real request doesn't pay CUDA init / kernel selection cost
        try:
            blank = Image.new("RGB", (856, 540), "white")
            await asyncio.to_thread(self._generate, blank, "Describe this image.", 8)
        except Exception:
            logger.exception("Warm-up failed (continuing)")
        logger.info("Model ready on device: %s", self._model.device)

    async def close(self) -> None:
        self._model = self._processor = None
        logger.info("Model unloaded.")

    async def is_ready(self) -> bool:
        return self._model is not None

    async def generate(
        self, image: Image.Image, prompt: str, json_schema: dict, max_new_tokens: int
    ) -> str:
        # transformers has no constrained decoding here; the prompt alone asks for JSON.
        # Blocking GPU work runs off the event loop so /health stays responsive.
        async with self._lock:
            return await asyncio.to_thread(self._generate, image, prompt, max_new_tokens)

    def _load(self) -> None:
        s = self._settings
        # Use the local copy if present, otherwise download from HuggingFace and keep a copy
        is_local = os.path.isdir(s.model_dir) and bool(os.listdir(s.model_dir))
        source = s.model_dir if is_local else s.model_id
        logger.info("Loading model from %s", source)

        self._processor = AutoProcessor.from_pretrained(
            source,
            # The API already downscales each image to its document's pixel limit
            size={"shortest_edge": s.min_pixels, "longest_edge": s.vision_max_pixels},
        )
        # bf16 is Qwen2.5-VL's native dtype; fp16 can overflow in the vision tower
        self._model = AutoModelForImageTextToText.from_pretrained(
            source,
            dtype=torch.bfloat16,
            device_map="auto",
            attn_implementation="sdpa",
        ).eval()

        if not is_local:
            logger.info("Saving model & processor to %s", s.model_dir)
            os.makedirs(s.model_dir, exist_ok=True)
            self._processor.save_pretrained(s.model_dir)
            self._model.save_pretrained(s.model_dir)

    def _generate(self, image: Image.Image, prompt: str, max_new_tokens: int) -> str:
        messages = [{
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": prompt},
            ],
        }]
        inputs = self._processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        ).to(self._model.device)

        with torch.inference_mode():
            outputs = self._model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                # Greedy decoding (generation_config.json has do_sample=true, temperature=1e-6)
                do_sample=False,
                temperature=None,
                top_p=None,
                top_k=None,
                # Default config uses 1.05, which penalizes repeated digits (e.g. NIK "000")
                repetition_penalty=1.0,
            )

        prompt_length = inputs["input_ids"].shape[-1]
        return self._processor.decode(outputs[0][prompt_length:], skip_special_tokens=True).strip()
