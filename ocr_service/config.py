import os
from dataclasses import dataclass

BACKENDS = ("hf", "vllm")


@dataclass(frozen=True)
class Settings:
    # "hf"   = load the model in-process with transformers
    # "vllm" = call a separate `vllm serve` instance (see run_vllm.sh); batches
    #          concurrent requests instead of serializing them
    backend: str = "vllm"

    model_id: str = "Qwen/Qwen2.5-VL-3B-Instruct"
    model_dir: str = "model/"
    max_new_tokens: int = 512
    max_upload_bytes: int = 10 * 1024 * 1024

    # Qwen2.5-VL default allows up to ~12.8M pixels (~16k visual tokens) per image.
    # An ID card is readable at ~1M pixels; capping this is the single biggest speed win.
    min_pixels: int = 256 * 28 * 28
    max_pixels: int = 1280 * 28 * 28
    # Upper bound of the vision processor (vLLM's --mm-processor-kwargs max_pixels). Must be at
    # least the largest per-document max_pixels in documents.py (Kartu Keluarga).
    vision_max_pixels: int = 3200 * 28 * 28

    vllm_url: str = "http://127.0.0.1:8071"
    vllm_model: str = "qwen-ktp"
    vllm_timeout: float = 120.0

    host: str = "0.0.0.0"
    port: int = 8070

    # Keys accepted in the X-API-Key header of /extract/*. Several keys allow rotating
    # without downtime. Empty disables authentication.
    api_keys: tuple[str, ...] = ()

    @classmethod
    def from_env(cls) -> "Settings":
        settings = cls(
            backend=os.getenv("INFERENCE_BACKEND", cls.backend).lower(),
            min_pixels=int(os.getenv("MIN_PIXELS", cls.min_pixels)),
            max_pixels=int(os.getenv("MAX_PIXELS", cls.max_pixels)),
            vllm_url=os.getenv("VLLM_URL", cls.vllm_url),
            vllm_model=os.getenv("VLLM_MODEL", cls.vllm_model),
            vllm_timeout=float(os.getenv("VLLM_TIMEOUT", cls.vllm_timeout)),
            host=os.getenv("HOST", cls.host),
            port=int(os.getenv("PORT", cls.port)),
            api_keys=tuple(k.strip() for k in os.getenv("API_KEYS", "").split(",") if k.strip()),
        )
        if settings.backend not in BACKENDS:
            raise ValueError(f"INFERENCE_BACKEND must be one of {BACKENDS}, got {settings.backend!r}")
        return settings
