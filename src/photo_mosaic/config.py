from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field, field_validator


class Strategy(StrEnum):
    GREEDY = "greedy"
    LAZY = "lazy"
    RANDOM = "random"
    FULL = "full"


class FitMode(StrEnum):
    STRETCH = "stretch"
    CROP = "crop"
    PAD = "pad"


class TileShape(StrEnum):
    RECT = "rect"
    HEX = "hex"


class HexBackground(StrEnum):
    SOURCE = "source"
    SOLID = "solid"


class MosaicConfig(BaseModel):
    source_image: Path
    tile_dirs: list[Path]
    output_path: Path
    tile_width: int = Field(default=16, ge=2, le=512)
    tile_height: int = Field(default=16, ge=2, le=512)
    output_width: int | None = Field(default=None, ge=32, le=20000)
    output_height: int | None = Field(default=None, ge=32, le=20000)
    tile_shape: TileShape = TileShape.RECT
    hex_overlap: float = Field(default=0.25, ge=0, lt=0.95)
    hex_edge_softness: float = Field(default=0.2, ge=0, le=1)
    hex_background: HexBackground = HexBackground.SOURCE
    fit_mode: FitMode = FitMode.CROP
    strategy: Strategy = Strategy.GREEDY
    max_repeats: int | None = Field(default=None, ge=1)
    max_usage_percent: float | None = Field(default=None, gt=0, le=100)
    lazy_randomness: float = Field(default=0.15, ge=0, le=1)
    lazy_top_k: int = Field(default=5, ge=1, le=200)
    random_steps: int = Field(default=0, ge=0, le=500000)
    full_steps: int = Field(default=2000, ge=0, le=1000000)
    cache_path: Path | None = None
    refresh_cache: bool = False

    @field_validator("tile_dirs")
    @classmethod
    def _ensure_tile_dirs(cls, value: list[Path]) -> list[Path]:
        if not value:
            raise ValueError("At least one tile directory is required")
        return value

    @property
    def tile_size(self) -> tuple[int, int]:
        return (self.tile_width, self.tile_height)
