# Photo Mosaic - Free [FaigleLabs]

Python photo mosaic application with both CLI and desktop GUI interfaces.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Build a mosaic

```bash
photo-mosaic build \
  --source /path/to/source.jpg \
  --tile-dir /path/to/tiles1 \
  --tile-dir /path/to/tiles2 \
  --output /path/to/output.png \
  --tile-width 16 \
  --tile-height 16 \
  --tile-shape hex \
  --hex-overlap 0.35 \
  --hex-edge-softness 0.3 \
  --hex-background source \
  --fit-mode crop \
  --strategy full \
  --full-steps 3000
```

## Launch GUI

```bash
photo-mosaic gui
```

## Notes

- Strategies:
  - `greedy`: fastest baseline matching.
  - `lazy`: top-k matching with controlled randomness (`--lazy-top-k`, `--lazy-randomness`).
  - `random`: greedy + random swap improvement (`--random-steps`).
  - `full`: greedy + bounded local optimization (`--full-steps`).
- Tile shapes:
  - `rect` (default): regular rectangular grid.
  - `hex`: staggered hexagonal layout with mask-aware matching and masked compositing.
  - Use `--hex-overlap` (`0.0` to `0.94`) to control vertical overlap density in hex mode.
  - Use `--hex-edge-softness` (`0.0` to `1.0`) to anti-alias hex edges.
  - Use `--hex-background source|solid` to choose what shows between hex edges.
- `--max-repeats` and `--max-usage-percent` enforce basic global usage constraints.
- `--cache-path .cache/tile_index.json` enables tile-index reuse.
