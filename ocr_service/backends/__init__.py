from ..config import Settings
from .base import InferenceBackend


def create_backend(settings: Settings) -> InferenceBackend:
    # Imported lazily so the vLLM backend never pulls in torch/transformers
    if settings.backend == "vllm":
        from .vllm import VLLMBackend
        return VLLMBackend(settings)

    from .hf import HFBackend
    return HFBackend(settings)


__all__ = ["InferenceBackend", "create_backend"]
