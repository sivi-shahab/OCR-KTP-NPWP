"""Heuristic fraud check: photocopies and photos taken of a laptop/phone screen.

Flag-only: the result is returned next to the OCR data and never blocks extraction.
Both detectors are classical signal checks (no model), so they run on CPU in the API
container while vLLM reads the document. They are tuned on simulated attacks only:
treat the scores as review hints and calibrate the thresholds on real captures.
"""

import numpy as np
from PIL import Image

from .schemas import FraudCheck

# Score at or above which a detector raises its flag
FLAG_THRESHOLD = 0.5

# --- Photocopy: a colour document that went through a b/w copier loses its colour ---------
_COLOUR_LONG_SIDE = 800
_CENTER = 0.6                 # measure the central part only, where the document usually is
_SATURATION_MIN = 0.15        # HSV saturation above which a pixel counts as coloured
_VALUE_RANGE = (0.2, 0.97)    # skip black text and blown-out highlights

# --- Screen recapture: the display's RGB subpixel grid aliases into moiré, i.e. sharp peaks
# in the spectrum (strongest in the colour channels: rainbow fringes) that printed documents
# and natural photos do not have ---------------------------------------------------------
_SPECTRUM_LONG_SIDE = 2048
_TILE = 256
_MIN_TILES = 4                # fewer textured tiles: too little image to judge
_MIN_RADIUS = 8               # below this the spectrum is the document layout, not a grid
# Text lines, table rules and card edges put periodic energy close to the axes, even when
# the document is a little rotated: luminance peaks within this angle are ignored.
_AXIS_CONE_DEGREES = 6.0
# Peak height (log magnitude above the radial mean, averaged over tiles) mapped to 0..1
_PEAK_RANGE = (2.0, 3.0)


def check_image(image: Image.Image, min_colour_fraction: float) -> FraudCheck:
    """`min_colour_fraction`: share of coloured pixels a genuine document of this type has."""
    colour_fraction = _colour_fraction(image)
    photocopy_score = float(np.clip(1 - colour_fraction / min_colour_fraction, 0, 1))
    peak = _spectral_peak(image)
    low, high = _PEAK_RANGE
    screen_score = float(np.clip((peak - low) / (high - low), 0, 1))

    is_photocopy = photocopy_score >= FLAG_THRESHOLD
    is_screen = screen_score >= FLAG_THRESHOLD
    signals = []
    if is_photocopy:
        signals.append("low_colour")
    if is_screen:
        signals.append("moire_pattern")
    return FraudCheck(
        suspicious=is_photocopy or is_screen,
        is_photocopy=is_photocopy,
        is_screen_recapture=is_screen,
        photocopy_score=round(photocopy_score, 3),
        screen_score=round(screen_score, 3),
        signals=signals,
    )


def _colour_fraction(image: Image.Image) -> float:
    """Share of the lit central pixels that are clearly coloured (not grey)."""
    small = image.copy()
    small.thumbnail((_COLOUR_LONG_SIDE, _COLOUR_LONG_SIDE))
    rgb = np.asarray(small, dtype=np.float32) / 255
    h, w, _ = rgb.shape
    mh, mw = int(h * (1 - _CENTER) / 2), int(w * (1 - _CENTER) / 2)
    rgb = rgb[mh:h - mh, mw:w - mw]

    value = rgb.max(axis=2)
    saturation = (value - rgb.min(axis=2)) / np.maximum(value, 1e-6)
    lit = (value >= _VALUE_RANGE[0]) & (value <= _VALUE_RANGE[1])
    if not lit.any():
        return 0.0
    return float((saturation[lit] > _SATURATION_MIN).mean())


def _spectral_peak(image: Image.Image) -> float:
    """Height of the strongest periodic component over the luminance and colour channels."""
    if max(image.size) > _SPECTRUM_LONG_SIDE:
        image = image.copy()
        image.thumbnail((_SPECTRUM_LONG_SIDE, _SPECTRUM_LONG_SIDE), Image.BOX)
    rgb = np.asarray(image, dtype=np.float32)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    luminance = rgb.mean(axis=2)
    red_green = r - g
    yellow_blue = (r + g) / 2 - b

    channels = [(luminance, _AXIS_CONE_DEGREES), (red_green, 0.0), (yellow_blue, 0.0)]
    peaks = [_channel_peak(pixels, cone) for pixels, cone in channels]
    return max(peaks)


def _channel_peak(pixels: np.ndarray, axis_cone_degrees: float) -> float:
    """Strongest spectral peak of one channel, in log magnitude above its radius' mean.

    Averaging spectra over tiles keeps a grid's peaks (same frequency everywhere) while
    the random maxima of text and noise cancel out.
    """
    h, w = pixels.shape
    window = np.outer(np.hanning(_TILE), np.hanning(_TILE))
    spectrum = np.zeros((_TILE, _TILE))
    tiles = 0
    for y in range(0, h - _TILE + 1, _TILE):
        for x in range(0, w - _TILE + 1, _TILE):
            tile = pixels[y:y + _TILE, x:x + _TILE]
            if tile.std() < 2:  # flat margin or background: no signal, only dilutes
                continue
            magnitude = np.abs(np.fft.fft2((tile - tile.mean()) * window))
            spectrum += np.log1p(np.fft.fftshift(magnitude))
            tiles += 1
    if tiles < _MIN_TILES:
        return 0.0
    spectrum /= tiles

    v, u = np.indices(spectrum.shape) - _TILE // 2
    radius = np.hypot(u, v).astype(int)
    radial_mean = np.bincount(radius.ravel(), spectrum.ravel()) / np.bincount(radius.ravel())
    residual = spectrum - radial_mean[radius]

    du, dv = np.abs(u), np.abs(v)
    angle_from_axis = np.degrees(np.arctan2(np.minimum(du, dv), np.maximum(du, dv)))
    block = _TILE // 8  # JPEG's 8x8 blocks put peaks at multiples of TILE/8
    mask = (
        (radius >= _MIN_RADIUS)
        & (radius < _TILE // 2 - 2)
        & (du > 2)
        & (dv > 2)
        & (angle_from_axis > axis_cone_degrees)
        & ~(_near_multiple(u, block) & _near_multiple(v, block))
    )
    return float(residual[mask].max())


def _near_multiple(values: np.ndarray, step: int) -> np.ndarray:
    offset = np.mod(values, step)
    return (offset <= 1) | (offset >= step - 1)
