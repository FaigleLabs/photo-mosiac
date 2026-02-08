from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from photo_mosaic.config import HexBackground, MosaicConfig, Strategy, TileShape
from photo_mosaic.core.image_utils import average_rgb, average_rgb_masked, fit_image, hex_mask
from photo_mosaic.core.strategies import (
    SelectionContext,
    full_optimize_assign,
    greedy_assign,
    lazy_assign,
    random_improve_assign,
)
from photo_mosaic.core.tile_index import TileDescriptor, build_tile_index


@dataclass(slots=True)
class LayoutPlan:
    positions: list[tuple[int, int]]
    canvas_size: tuple[int, int]


def _compute_layout(source_size: tuple[int, int], config: MosaicConfig) -> LayoutPlan:
    tile_w, tile_h = config.tile_size
    out_w = config.output_width or source_size[0]
    out_h = config.output_height or source_size[1]

    if config.tile_shape == TileShape.HEX:
        v_step = max(1, int(round(tile_h * (1.0 - config.hex_overlap))))
        cols = max(1, (out_w - (tile_w // 2)) // tile_w)
        rows = max(1, ((out_h - tile_h) // v_step) + 1) if out_h > tile_h else 1

        positions: list[tuple[int, int]] = []
        for row in range(rows):
            x_offset = tile_w // 2 if row % 2 else 0
            y = row * v_step
            for col in range(cols):
                x = x_offset + col * tile_w
                positions.append((x, y))

        width = cols * tile_w + (tile_w // 2)
        height = tile_h + max(0, (rows - 1) * v_step)
        return LayoutPlan(positions=positions, canvas_size=(width, height))

    cols = max(1, out_w // tile_w)
    rows = max(1, out_h // tile_h)
    positions = [(col * tile_w, row * tile_h) for row in range(rows) for col in range(cols)]
    return LayoutPlan(positions=positions, canvas_size=(cols * tile_w, rows * tile_h))


def _source_cell_rgbs(
    source_image: Image.Image,
    layout: LayoutPlan,
    tile_size: tuple[int, int],
    tile_shape: TileShape,
    hex_edge_softness: float,
) -> np.ndarray:
    tile_w, tile_h = tile_size
    resized = source_image.convert("RGB")
    if resized.size != layout.canvas_size:
        resized = resized.resize(layout.canvas_size, Image.Resampling.BICUBIC)

    rgbs: list[tuple[float, float, float]] = []
    max_x = max(0, layout.canvas_size[0] - tile_w)
    max_y = max(0, layout.canvas_size[1] - tile_h)
    mask = hex_mask(tile_size, edge_softness=hex_edge_softness) if tile_shape == TileShape.HEX else None

    for x, y in layout.positions:
        left = min(x, max_x)
        top = min(y, max_y)
        patch = resized.crop((left, top, left + tile_w, top + tile_h))
        if mask is None:
            rgbs.append(average_rgb(patch))
        else:
            rgbs.append(average_rgb_masked(patch, mask))

    return np.array(rgbs, dtype=np.float32)


def _compose(
    assignments: list[int],
    tiles: list[TileDescriptor],
    layout: LayoutPlan,
    tile_size: tuple[int, int],
    fit_mode,
    tile_shape: TileShape,
    hex_edge_softness: float,
    base_image: Image.Image | None,
) -> Image.Image:
    canvas = base_image.copy() if base_image is not None else Image.new("RGB", layout.canvas_size)
    rendered_cache: dict[Path, Image.Image] = {}
    mask = hex_mask(tile_size, edge_softness=hex_edge_softness) if tile_shape == TileShape.HEX else None

    for i, tile_index in enumerate(assignments):
        x, y = layout.positions[i]
        tile_path = tiles[tile_index].path
        tile_image = rendered_cache.get(tile_path)
        if tile_image is None:
            with Image.open(tile_path) as raw_tile:
                tile_image = fit_image(raw_tile.convert("RGB"), tile_size, fit_mode=fit_mode)
            rendered_cache[tile_path] = tile_image

        if mask is None:
            canvas.paste(tile_image, (x, y))
        else:
            canvas.paste(tile_image, (x, y), mask)

    return canvas


def build_mosaic(config: MosaicConfig) -> Path:
    base_image: Image.Image | None = None
    with Image.open(config.source_image) as source:
        layout = _compute_layout(source.size, config)
        source_for_layout = source.convert("RGB").resize(layout.canvas_size, Image.Resampling.BICUBIC)
        source_rgbs = _source_cell_rgbs(
            source_for_layout,
            layout=layout,
            tile_size=config.tile_size,
            tile_shape=config.tile_shape,
            hex_edge_softness=config.hex_edge_softness,
        )
        if config.tile_shape == TileShape.HEX and config.hex_background == HexBackground.SOURCE:
            base_image = source_for_layout

    tiles = build_tile_index(
        tile_dirs=config.tile_dirs,
        tile_size=config.tile_size,
        fit_mode=config.fit_mode,
        tile_shape=config.tile_shape,
        hex_edge_softness=config.hex_edge_softness,
        cache_path=config.cache_path,
        refresh_cache=config.refresh_cache,
    )
    if not tiles:
        raise ValueError("No valid tile images were found in the provided directories")

    selection_context = SelectionContext(
        max_repeats=config.max_repeats,
        max_usage_percent=config.max_usage_percent,
        total_tiles=len(layout.positions),
    )
    if config.strategy == Strategy.LAZY:
        assignments = lazy_assign(
            source_rgbs,
            tiles=tiles,
            ctx=selection_context,
            top_k=config.lazy_top_k,
            randomness=config.lazy_randomness,
        )
    else:
        assignments = greedy_assign(source_rgbs, tiles=tiles, ctx=selection_context)

    if config.strategy == Strategy.RANDOM:
        assignments = random_improve_assign(
            source_rgbs,
            tiles=tiles,
            initial_assignments=assignments,
            steps=config.random_steps,
        )
    elif config.strategy == Strategy.FULL:
        assignments = full_optimize_assign(
            source_rgbs,
            tiles=tiles,
            initial_assignments=assignments,
            ctx=selection_context,
            steps=config.full_steps,
        )

    output_image = _compose(
        assignments=assignments,
        tiles=tiles,
        layout=layout,
        tile_size=config.tile_size,
        fit_mode=config.fit_mode,
        tile_shape=config.tile_shape,
        hex_edge_softness=config.hex_edge_softness,
        base_image=base_image,
    )
    config.output_path.parent.mkdir(parents=True, exist_ok=True)
    output_image.save(config.output_path)
    return config.output_path
