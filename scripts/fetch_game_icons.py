#!/usr/bin/env python3
"""Download free-use Satisfactory icons from the Fandom wiki into the frontend.

The wiki (https://satisfactory.fandom.com) hosts item/building icons under
``Category:Icons``. This script resolves each named ``File:<Name>.png`` to its
CDN URL via the MediaWiki API and downloads it to
``frontend/public/assets/icons/<group>/<key>.png`` — the paths the map's icon
system (``frontend/src/utils/mapIcons.ts``) looks up.

Run once (icons rarely change):

    python scripts/fetch_game_icons.py

Files that fail to resolve are reported and skipped; the map falls back to its
built-in SVG glyph for any missing icon, so a partial fetch is safe.
"""

from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

_API = "https://satisfactory.fandom.com/api.php"
_OUT = Path(__file__).resolve().parents[1] / "frontend" / "public" / "assets" / "icons"
_UA = "SpiffCoCommandCenter/1.0 (personal self-hosted tool)"

# group -> { local key : wiki File name (without the "File:" prefix / ".png") }
ICONS: dict[str, dict[str, str]] = {
    "resource": {
        "iron-ore": "Iron Ore",
        "copper-ore": "Copper Ore",
        "caterium-ore": "Caterium Ore",
        "coal": "Coal",
        "limestone": "Limestone",
        "raw-quartz": "Raw Quartz",
        "sulfur": "Sulfur",
        "bauxite": "Bauxite",
        "uranium": "Uranium",
        "sam": "SAM",
        "crude-oil": "Crude Oil",
        "water": "Water",
        "nitrogen-gas": "Nitrogen Gas",
    },
    "pickup": {
        "somersloop": "Somersloop",
        "mercer-sphere": "Mercer Sphere",
        "blue-power-slug": "Blue Power Slug",
        "yellow-power-slug": "Yellow Power Slug",
        "purple-power-slug": "Purple Power Slug",
        "crash-site": "Hard Drive",
    },
    "type": {
        "geyser": "Geothermal Generator",
        "train_station": "Train Station",
        "drone_port": "Drone Port",
        "truck_station": "Truck Station",
        "power_plant": "Power Line",
        "factory": "Manufacturer",
    },
}


def resolve_url(file_name: str) -> str | None:
    """Return the CDN URL for ``File:<file_name>.png`` or None if not found."""
    params = urllib.parse.urlencode(
        {
            "action": "query",
            "titles": f"File:{file_name}.png",
            "prop": "imageinfo",
            "iiprop": "url",
            "format": "json",
        }
    )
    req = urllib.request.Request(f"{_API}?{params}", headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=20) as resp:  # noqa: S310 - fixed host
        data = json.load(resp)
    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        info = page.get("imageinfo")
        if info:
            return str(info[0]["url"])
    return None


def download(url: str, dest: Path) -> int:
    """Download ``url`` to ``dest``; return bytes written."""
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 - wiki CDN
        data = resp.read()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return len(data)


def main() -> int:
    ok: dict[str, list[str]] = {}
    failed: list[str] = []
    for group, entries in ICONS.items():
        for key, file_name in entries.items():
            try:
                url = resolve_url(file_name)
                if not url:
                    failed.append(f"{group}/{key} (File:{file_name}.png not found)")
                    continue
                # Fandom's CDN serves WebP regardless of the .png URL.
                size = download(url, _OUT / group / f"{key}.webp")
                ok.setdefault(group, []).append(f"{key} ({size // 1024}KB)")
            except Exception as exc:  # noqa: BLE001 - report and continue
                failed.append(f"{group}/{key}: {exc}")

    for group, items in ok.items():
        print(f"[{group}] {len(items)}: {', '.join(items)}")
    if failed:
        print(f"\nFAILED ({len(failed)}):")
        for f in failed:
            print(f"  - {f}")
    print(f"\nIcons written under {_OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
