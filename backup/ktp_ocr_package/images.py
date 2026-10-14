from io import BytesIO

from PIL import Image

ALLOWED_CONTENT_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})


class InvalidImageError(ValueError):
    """The uploaded bytes could not be decoded as an image."""


def decode_image(data: bytes) -> Image.Image:
    try:
        return Image.open(BytesIO(data)).convert("RGB")
    except Exception as exc:
        raise InvalidImageError(f"Failed to read image: {exc}") from exc


def limit_pixels(image: Image.Image, max_pixels: int) -> Image.Image:
    """Downscale (keeping aspect ratio) so the image has at most `max_pixels` pixels."""
    width, height = image.size
    if width * height <= max_pixels:
        return image
    scale = (max_pixels / (width * height)) ** 0.5
    return image.resize((int(width * scale), int(height * scale)), Image.LANCZOS)
