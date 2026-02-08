from __future__ import annotations

from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageOps

from photo_mosaic.config import FitMode


def fit_image(image: Image.Image, target_size: tuple[int, int], fit_mode: FitMode) -> Image.Image:
    if fit_mode == FitMode.STRETCH:
        return image.resize(target_size, Image.Resampling.BICUBIC)
    if fit_mode == FitMode.CROP:
        return ImageOps.fit(image, target_size, method=Image.Resampling.BICUBIC, centering=(0.5, 0.5))
    # PAD keeps full image and letterboxes to the target.
    return ImageOps.pad(image, target_size, method=Image.Resampling.BICUBIC, color=(0, 0, 0))


def average_rgb(image: Image.Image) -> tuple[float, float, float]:
    pixels = image.convert("RGB").getdata()
    count = len(pixels)
    r = g = b = 0
    for pr, pg, pb in pixels:
        r += pr
        g += pg
        b += pb
    return (r / count, g / count, b / count)


def average_rgb_masked(image: Image.Image, mask: Image.Image) -> tuple[float, float, float]:
    rgb = np.asarray(image.convert("RGB"), dtype=np.float32)
    weights = np.asarray(mask.convert("L"), dtype=np.float32) / 255.0
    total = float(weights.sum())
    if total <= 0:
        return average_rgb(image)

    # Weighted mean over visible mask area.
    weighted = rgb * weights[:, :, None]
    channel_sum = weighted.sum(axis=(0, 1))
    return (float(channel_sum[0] / total), float(channel_sum[1] / total), float(channel_sum[2] / total))


@lru_cache(maxsize=64)
def _cached_hex_mask(width: int, height: int, softness_bucket: int) -> Image.Image:
    # Supersample then downscale for anti-aliased hex edges.
    scale = 4
    mask_large = Image.new("L", (width * scale, height * scale), 0)
    inset = softness_bucket / 1000.0

    x_min = inset * width
    x_max = width - x_min
    y_min = inset * height
    y_max = height - y_min
    y_upper = y_min + (y_max - y_min) * 0.25
    y_lower = y_min + (y_max - y_min) * 0.75
    points = [
        (width * 0.5, y_min),
        (x_max, y_upper),
        (x_max, y_lower),
        (width * 0.5, y_max),
        (x_min, y_lower),
        (x_min, y_upper),
    ]
    points_large = [(x * scale, y * scale) for x, y in points]

    draw = ImageDraw.Draw(mask_large)
    draw.polygon(points_large, fill=255)
    return mask_large.resize((width, height), Image.Resampling.LANCZOS)


def hex_mask(size: tuple[int, int], edge_softness: float = 0.2) -> Image.Image:
    width, height = size
    # Convert 0..1 softness to a small proportional inset.
    inset = min(max(edge_softness, 0.0), 1.0) * 0.08
    return _cached_hex_mask(width, height, int(round(inset * 1000)))
