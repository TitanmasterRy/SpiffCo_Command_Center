"""Generate the world-map tile pyramid from the bundled 8K map render.

Slices ``frontend/public/assets/satisfactory-map.avif`` (8192x8192, covering the
exact 750x750 km world extent, see ``frontend/src/utils/mapCoords.ts``) into a
standard XYZ tile pyramid at ``frontend/public/assets/map-tiles/{z}/{x}/{y}.webp``
for zoom levels 0..MAX_ZOOM. Zoom z has 2^z x 2^z tiles of 256px, so MAX_ZOOM=5
consumes the full native resolution (256 * 2^5 = 8192).

Run from the repo root (requires Pillow with AVIF support)::

    python scripts/generate_map_tiles.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

TILE_SIZE = 256
MAX_ZOOM = 5
WEBP_QUALITY = 82

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE = REPO_ROOT / "frontend" / "public" / "assets" / "satisfactory-map.avif"
OUT_DIR = REPO_ROOT / "frontend" / "public" / "assets" / "map-tiles"


def slice_zoom(image: Image.Image, zoom: int) -> int:
    """Write all tiles for one zoom level; returns the tile count."""
    tiles_per_side = 2**zoom
    target = TILE_SIZE * tiles_per_side
    scaled = image if image.width == target else image.resize((target, target), Image.LANCZOS)
    count = 0
    for x in range(tiles_per_side):
        column = OUT_DIR / str(zoom) / str(x)
        column.mkdir(parents=True, exist_ok=True)
        for y in range(tiles_per_side):
            box = (x * TILE_SIZE, y * TILE_SIZE, (x + 1) * TILE_SIZE, (y + 1) * TILE_SIZE)
            scaled.crop(box).save(column / f"{y}.webp", "WEBP", quality=WEBP_QUALITY)
            count += 1
    return count


def main() -> None:
    image = Image.open(SOURCE).convert("RGB")
    expected = TILE_SIZE * 2**MAX_ZOOM
    if image.size != (expected, expected):
        raise SystemExit(f"expected {expected}x{expected} source, got {image.size[0]}x{image.size[1]}")
    total = 0
    for zoom in range(MAX_ZOOM, -1, -1):
        total += slice_zoom(image, zoom)
        print(f"zoom {zoom}: done")
    print(f"{total} tiles written to {OUT_DIR}")


if __name__ == "__main__":
    main()
