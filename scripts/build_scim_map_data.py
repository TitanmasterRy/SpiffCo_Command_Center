#!/usr/bin/env python3
"""Vendor SCIM (satisfactory-calculator.com Interactive Map) layer data locally.

Fetches the interactive map's layer definition JSON and turns it into local
assets the frontend serves itself (no runtime dependency on their site):

* ``frontend/src/data/scimLayers.json`` — the filter taxonomy: categories →
  groups → layers with SCIM's outside/inside colors, purity, local icon path,
  and a ``match`` descriptor used to map our live FRM world features onto SCIM
  layer ids.
* ``frontend/public/assets/scim/static-layers.json`` — marker positions and
  polygons for world content FRM has no endpoint for (wild food, spore flowers,
  gas pillars, rocks, caves, roads, world border, spawn points).
* ``frontend/public/assets/icons/scim/<name>.png`` — the layer icons.

Run once from the repo root (icons and world geometry rarely change)::

    python scripts/build_scim_map_data.py [path/to/raw.json]

Passing a pre-downloaded raw JSON skips the network fetch of the definition
(icons are still downloaded unless already present).
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any

_SOURCE = "https://satisfactory-calculator.com/en/interactive-map/index/json"
_UA = "SpiffCoCommandCenter/1.0 (personal self-hosted tool)"

_REPO = Path(__file__).resolve().parents[1]
_LAYERS_OUT = _REPO / "frontend" / "src" / "data" / "scimLayers.json"
_STATIC_OUT = _REPO / "frontend" / "public" / "assets" / "scim" / "static-layers.json"
_ICONS_OUT = _REPO / "frontend" / "public" / "assets" / "icons" / "scim"
_ICON_PUBLIC_BASE = "/assets/icons/scim"

# SCIM purity enum → our meta.purity values (note SCIM's "Inpure" typo).
_PURITY = {"RP_Inpure": "impure", "RP_Normal": "normal", "RP_Pure": "pure"}

# SCIM group class name → our FRM resource slug (see connectors/frm/normalize.py).
_RESOURCE_SLUG = {
    "Desc_Stone_C": "limestone",
    "Desc_OreIron_C": "iron-ore",
    "Desc_OreCopper_C": "copper-ore",
    "Desc_OreGold_C": "caterium-ore",
    "Desc_Coal_C": "coal",
    "Desc_LiquidOil_C": "crude-oil",
    "Desc_LiquidOilWell_C": "crude-oil",
    "Desc_Sulfur_C": "sulfur",
    "Desc_OreBauxite_C": "bauxite",
    "Desc_RawQuartz_C": "raw-quartz",
    "Desc_OreUranium_C": "uranium",
    "Desc_SAM_C": "sam",
    "Desc_NitrogenGas_C": "nitrogen-gas",
    "Desc_Water_C": "water",
}

# Live pickup layers → our feature meta.kind slug (SCIM's greenSlugs are the
# in-game *blue* power slugs).
_PICKUP_KIND = {
    "greenSlugs": "blue-power-slug",
    "yellowSlugs": "yellow-power-slug",
    "purpleSlugs": "purple-power-slug",
    "somersloops": "somersloop",
    "mercerSpheres": "mercer-sphere",
    "hardDrives": "crash-site",
}

# Static-only layers (FRM has no endpoint) vendored with their positions.
_STATIC_POINT_LAYERS = {
    "paleBerry", "berylNut", "baconAgaric",  # wild food
    "sporeFlowers", "pillars", "smallRocks", "largeRocks",  # hazards / rocks
}
_WORLD_CATEGORY = {
    "spawn": "Spawn points",
    "worldBorder": "World border",
    "caves": "Caves",
    "roads": "Roads",
    "sporeFlowers": "Spore Flowers",
    "pillars": "Gas Pillars",
    "smallRocks": "Small Rocks",
    "largeRocks": "Large Rocks",
}


def _fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept": "*/*"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def _icon_filename(url: str) -> str:
    name = url.rsplit("/", 1)[-1].split("?")[0]
    return re.sub(r"[^A-Za-z0-9._-]", "", name)


def _download_icons(urls: set[str]) -> dict[str, str]:
    """Download each icon once; returns remote URL → public local path."""
    _ICONS_OUT.mkdir(parents=True, exist_ok=True)
    mapping: dict[str, str] = {}
    for url in sorted(urls):
        filename = _icon_filename(url)
        target = _ICONS_OUT / filename
        if not target.exists():
            try:
                target.write_bytes(_fetch(url))
            except OSError as error:  # pragma: no cover - network dependent
                print(f"  ! icon failed, skipped: {url} ({error})")
                continue
        mapping[url] = f"{_ICON_PUBLIC_BASE}/{filename}"
    return mapping


def _match_for(layer_id: str, group_type: str | None, purity: str | None,
               category_id: str) -> dict[str, str] | None:
    """Descriptor used by the frontend to map live features to this layer."""
    if layer_id in _PICKUP_KIND:
        return {"kind": "pickup", "pickup": _PICKUP_KIND[layer_id]}
    if purity is None:
        return None
    resource = _RESOURCE_SLUG.get(group_type or "")
    if layer_id.startswith("geyser"):
        return {"kind": "geyser", "purity": purity}
    if resource is None:
        return None
    well = "well" if category_id == "resource_wells" else "node"
    return {"kind": well, "resource": resource, "purity": purity}


def build() -> None:
    if len(sys.argv) > 1:
        raw = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    else:
        print(f"Fetching {_SOURCE} ...")
        raw = json.loads(_fetch(_SOURCE))

    icon_urls = {
        option["icon"]
        for category in raw["options"]
        for group in category["options"]
        for option in group.get("options", [])
        if option.get("icon")
    }
    print(f"Downloading {len(icon_urls)} icons ...")
    icon_map = _download_icons(icon_urls)

    categories: list[dict[str, Any]] = []
    static_layers: dict[str, Any] = {}

    for category in raw["options"]:
        category_id = category.get("tabId") or "world"
        category_name = category.get("name") or "World"
        groups: list[dict[str, Any]] = []
        for group in category["options"]:
            layers: list[dict[str, Any]] = []
            for option in group.get("options", []):
                layer_id = option["layerId"]
                markers = option.get("markers") or []
                if layer_id in ("spawn", "worldBorder", "caves", "roads"):
                    # Geometry layers keep their raw shapes (positions in cm).
                    static_layers[layer_id] = (
                        option.get("polygon") if layer_id == "worldBorder" else markers
                    )
                elif layer_id in _STATIC_POINT_LAYERS:
                    static_layers[layer_id] = [
                        [marker["x"], marker["y"], marker.get("z", 0)] for marker in markers
                    ]
                purity = _PURITY.get(option.get("purity") or "")
                layer: dict[str, Any] = {
                    "id": layer_id,
                    "name": option.get("name") or _WORLD_CATEGORY.get(layer_id, layer_id),
                    "outsideColor": option.get("outsideColor"),
                    "insideColor": option.get("insideColor"),
                    "icon": icon_map.get(option.get("icon") or ""),
                    "purity": purity,
                    "static": layer_id in _STATIC_POINT_LAYERS
                    or layer_id in ("spawn", "worldBorder", "caves", "roads"),
                    "count": len(markers),
                }
                match = _match_for(layer_id, group.get("type"), purity, category_id)
                if match:
                    layer["match"] = match
                # Player-save-only layers have no data source here; skip them.
                if layer_id in ("playerResourceDepositsLayer", "playerItemsPickupLayer",
                                "unknown", "unknownWell", "geyserUnknown"):
                    continue
                layers.append(layer)
            if layers:
                groups.append({
                    "name": group.get("name") or _WORLD_CATEGORY.get(layers[0]["id"], "World"),
                    "type": group.get("type"),
                    "layers": layers,
                })
        categories.append({"id": category_id, "name": category_name, "groups": groups})

    _LAYERS_OUT.parent.mkdir(parents=True, exist_ok=True)
    _LAYERS_OUT.write_text(
        json.dumps({"categories": categories}, indent=2) + "\n", encoding="utf-8"
    )
    _STATIC_OUT.parent.mkdir(parents=True, exist_ok=True)
    _STATIC_OUT.write_text(json.dumps(static_layers, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {_LAYERS_OUT.relative_to(_REPO)} ({len(categories)} categories)")
    size_kb = _STATIC_OUT.stat().st_size / 1024
    print(f"Wrote {_STATIC_OUT.relative_to(_REPO)} ({size_kb:.0f} KiB)")


if __name__ == "__main__":
    build()
