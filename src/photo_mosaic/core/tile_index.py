from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from photo_mosaic.cache import load_json, write_json
from photo_mosaic.config import FitMode, TileShape
from photo_mosaic.core.image_utils import average_rgb, average_rgb_masked, fit_image, hex_mask

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


@dataclass(slots=True)
class TileDescriptor:
    path: Path
    avg_rgb: tuple[float, float, float]


def _iter_image_paths(tile_dirs: list[Path]) -> list[Path]:
    results: list[Path] = []
    for tile_dir in tile_dirs:
        if not tile_dir.exists():
            continue
        for path in tile_dir.rglob("*"):
            if path.suffix.lower() in IMAGE_EXTENSIONS and path.is_file():
                results.append(path)
    return sorted(set(results))


def _from_cache(data: dict, fit_mode: FitMode, tile_size: tuple[int, int], tile_shape: TileShape) -> list[TileDescriptor] | None:
    settings = data.get("settings", {})
    if settings.get("fit_mode") != fit_mode.value:
        return None
    if tuple(settings.get("tile_size", [])) != tile_size:
        return None
    if settings.get("tile_shape", TileShape.RECT.value) != tile_shape.value:
        return None

    descriptors: list[TileDescriptor] = []
    for entry in data.get("tiles", []):
        descriptors.append(
            TileDescriptor(
                path=Path(entry["path"]),
                avg_rgb=(float(entry["avg_rgb"][0]), float(entry["avg_rgb"][1]), float(entry["avg_rgb"][2])),
            )
        )
    return descriptors


def _to_cache(
    descriptors: list[TileDescriptor], fit_mode: FitMode, tile_size: tuple[int, int], tile_shape: TileShape, hex_edge_softness: float
) -> dict:
    return {
        "settings": {
            "fit_mode": fit_mode.value,
            "tile_size": list(tile_size),
            "tile_shape": tile_shape.value,
            "hex_edge_softness": round(hex_edge_softness, 3),
        },
        "tiles": [{"path": str(d.path), "avg_rgb": list(d.avg_rgb)} for d in descriptors],
    }


def build_tile_index(
    tile_dirs: list[Path],
    tile_size: tuple[int, int],
    fit_mode: FitMode,
    tile_shape: TileShape = TileShape.RECT,
    hex_edge_softness: float = 0.2,
    cache_path: Path | None = None,
    refresh_cache: bool = False,
) -> list[TileDescriptor]:
    if cache_path and not refresh_cache:
        cached = load_json(cache_path)
        if cached is not None:
            parsed = _from_cache(cached, fit_mode=fit_mode, tile_size=tile_size, tile_shape=tile_shape)
            cached_softness = float(cached.get("settings", {}).get("hex_edge_softness", 0.2))
            if parsed and (tile_shape != TileShape.HEX or round(cached_softness, 3) == round(hex_edge_softness, 3)):
                return parsed

    descriptors: list[TileDescriptor] = []
    masked_avg = tile_shape == TileShape.HEX
    mask = hex_mask(tile_size, edge_softness=hex_edge_softness) if masked_avg else None
    for path in _iter_image_paths(tile_dirs):
        try:
            with Image.open(path) as img:
                tile = fit_image(img.convert("RGB"), tile_size, fit_mode=fit_mode)
                avg = average_rgb_masked(tile, mask) if mask is not None else average_rgb(tile)
                descriptors.append(TileDescriptor(path=path, avg_rgb=avg))
        except Exception:
            continue

    if cache_path is not None:
        write_json(
            cache_path,
            _to_cache(
                descriptors,
                fit_mode=fit_mode,
                tile_size=tile_size,
                tile_shape=tile_shape,
                hex_edge_softness=hex_edge_softness,
            ),
        )
    return descriptors
