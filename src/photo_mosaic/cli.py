from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from photo_mosaic.config import FitMode, HexBackground, MosaicConfig, Strategy, TileShape
from photo_mosaic.core.mosaic import build_mosaic

app = typer.Typer(help="Photo Mosaic - Free [FaigleLabs]")
console = Console()


@app.command("build")
def build_command(
    source_image: Path = typer.Option(..., "--source", exists=True, readable=True, help="Path to source image"),
    tile_dir: list[Path] = typer.Option(..., "--tile-dir", exists=True, file_okay=False, dir_okay=True, help="Tile directory, can be repeated"),
    output_path: Path = typer.Option(..., "--output", help="Output image path"),
    tile_width: int = typer.Option(16, "--tile-width", min=2, max=512),
    tile_height: int = typer.Option(16, "--tile-height", min=2, max=512),
    output_width: int | None = typer.Option(None, "--output-width", min=32, max=20000),
    output_height: int | None = typer.Option(None, "--output-height", min=32, max=20000),
    tile_shape: TileShape = typer.Option(TileShape.RECT, "--tile-shape", case_sensitive=False),
    hex_overlap: float = typer.Option(0.25, "--hex-overlap", min=0.0, max=0.94),
    hex_edge_softness: float = typer.Option(0.2, "--hex-edge-softness", min=0.0, max=1.0),
    hex_background: HexBackground = typer.Option(HexBackground.SOURCE, "--hex-background", case_sensitive=False),
    fit_mode: FitMode = typer.Option(FitMode.CROP, "--fit-mode", case_sensitive=False),
    strategy: Strategy = typer.Option(Strategy.GREEDY, "--strategy", case_sensitive=False),
    max_repeats: int | None = typer.Option(None, "--max-repeats", min=1),
    max_usage_percent: float | None = typer.Option(None, "--max-usage-percent", min=0.01, max=100.0),
    lazy_randomness: float = typer.Option(0.15, "--lazy-randomness", min=0.0, max=1.0),
    lazy_top_k: int = typer.Option(5, "--lazy-top-k", min=1, max=200),
    random_steps: int = typer.Option(0, "--random-steps", min=0, max=500000),
    full_steps: int = typer.Option(2000, "--full-steps", min=0, max=1000000),
    cache_path: Path | None = typer.Option(None, "--cache-path", help="Path to tile index cache JSON"),
    refresh_cache: bool = typer.Option(False, "--refresh-cache", help="Force recomputing cache"),
) -> None:
    config = MosaicConfig(
        source_image=source_image,
        tile_dirs=tile_dir,
        output_path=output_path,
        tile_width=tile_width,
        tile_height=tile_height,
        output_width=output_width,
        output_height=output_height,
        tile_shape=tile_shape,
        hex_overlap=hex_overlap,
        hex_edge_softness=hex_edge_softness,
        hex_background=hex_background,
        fit_mode=fit_mode,
        strategy=strategy,
        max_repeats=max_repeats,
        max_usage_percent=max_usage_percent,
        lazy_randomness=lazy_randomness,
        lazy_top_k=lazy_top_k,
        random_steps=random_steps,
        full_steps=full_steps,
        cache_path=cache_path,
        refresh_cache=refresh_cache,
    )

    try:
        result = build_mosaic(config)
    except Exception as exc:
        console.print(f"[red]Build failed:[/red] {exc}")
        raise typer.Exit(1) from exc

    console.print(f"[green]Mosaic created:[/green] {result}")


@app.command("gui")
def gui_command() -> None:
    from photo_mosaic.gui import launch_gui

    launch_gui()


if __name__ == "__main__":
    app()
