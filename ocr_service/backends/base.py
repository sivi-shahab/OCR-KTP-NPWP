from abc import ABC, abstractmethod

from PIL import Image


class InferenceBackend(ABC):
    """Runs the vision-language model: image + prompt in, raw model text out."""

    name: str

    async def start(self) -> None:
        """Load resources. Called once at application startup."""

    async def close(self) -> None:
        """Release resources. Called once at application shutdown."""

    @abstractmethod
    async def is_ready(self) -> bool: ...

    @abstractmethod
    async def generate(self, image: Image.Image, prompt: str, json_schema: dict) -> str:
        """Return the model's raw answer. Backends that support it constrain output to `json_schema`."""
