from __future__ import annotations

from pathlib import Path

from PIL import Image
from typer.testing import CliRunner

from photo_mosaic.cli import app


def _make_image(path: Path, color: tuple[int, int, int], size: tuple[int, int] = (64, 64)) -> None:
    img = Image.new("RGB", size, color)
    img.save(path)


def test_build_cli_smoke(tmp_path: Path) -> None:
    tiles = tmp_path / "tiles"
    tiles.mkdir()
    _make_image(tiles / "r.png", (255, 0, 0))
    _make_image(tiles / "g.png", (0, 255, 0))
    _make_image(tiles / "b.png", (0, 0, 255))

    source = tmp_path / "source.png"
    _make_image(source, (200, 0, 10), size=(64, 64))

    out = tmp_path / "out.png"

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "build",
            "--source",
            str(source),
            "--tile-dir",
            str(tiles),
            "--output",
            str(out),
            "--tile-width",
            "16",
            "--tile-height",
            "16",
            "--fit-mode",
            "crop",
            "--strategy",
            "greedy",
        ],
    )

    assert result.exit_code == 0, result.output
    assert out.exists()


def test_build_cli_hex_smoke(tmp_path: Path) -> None:
    tiles = tmp_path / "tiles"
    tiles.mkdir()
    _make_image(tiles / "r.png", (255, 0, 0))
    _make_image(tiles / "g.png", (0, 255, 0))
    _make_image(tiles / "b.png", (0, 0, 255))

    source = tmp_path / "source.png"
    _make_image(source, (20, 120, 220), size=(96, 96))

    out = tmp_path / "out_hex.png"

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "build",
            "--source",
            str(source),
            "--tile-dir",
            str(tiles),
            "--output",
            str(out),
            "--tile-width",
            "20",
            "--tile-height",
            "20",
            "--tile-shape",
            "hex",
            "--hex-overlap",
            "0.35",
            "--hex-edge-softness",
            "0.3",
            "--hex-background",
            "source",
            "--fit-mode",
            "crop",
            "--strategy",
            "lazy",
            "--lazy-top-k",
            "3",
        ],
    )

    assert result.exit_code == 0, result.output
    assert out.exists()
