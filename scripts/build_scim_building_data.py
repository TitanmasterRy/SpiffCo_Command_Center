#!/usr/bin/env python3
"""Vendor SCIM's building footprint outlines and map colors locally.

Merges two satisfactory-calculator.com sources into one local asset:

* ``detailedModels.json`` — hand-drawn top-down outline polygons for ~130
  buildings (points in cm relative to the building center, pre-rotation).
* ``/en/api/game`` ``buildingsData`` — per-class map color/opacity/weight and
  the generic footprint (width × length in meters) for every building.

Output: ``frontend/public/assets/scim/building-models.json`` keyed by the short
class name FRM reports (e.g. ``Build_SmelterMk1_C``)::

    {
      "Build_SmelterMk1_C": {
        "name": "Smelter", "category": "production",
        "color": "#FF0000", "opacity": 0.75, "weight": 2,
        "width": 6, "length": 9,          # meters (rectangle fallback)
        "scale": 0.9,                      # detailed-outline point scale
        "forms": [{"points": [[x,y],...], "holes": [...]}]  # cm, optional
      }, ...
    }

Run once from the repo root (outlines rarely change)::

    python scripts/build_scim_building_data.py [detailedModels.json] [game.json]

Pre-downloaded files skip the network fetches.
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path
from typing import Any

_MODELS_URL = "https://static.satisfactory-calculator.com/js/InteractiveMap/build/detailedModels.json"
_GAME_URL = "https://satisfactory-calculator.com/en/api/game"
_UA = "Mozilla/5.0 (SpiffCoCommandCenter personal self-hosted tool)"

_REPO = Path(__file__).resolve().parents[1]
_OUT = _REPO / "frontend" / "public" / "assets" / "scim" / "building-models.json"


def _fetch_json(url: str) -> Any:
    request = urllib.request.Request(
        url, headers={"User-Agent": _UA, "Accept": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)


def _short_class(full_path: str) -> str:
    """'/Game/.../Build_X.Build_X_C' → 'Build_X_C' (FRM's ClassName form)."""
    return full_path.rsplit(".", 1)[-1]


def build() -> None:
    models_raw = (
        json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
        if len(sys.argv) > 1
        else _fetch_json(_MODELS_URL)
    )
    game_raw = (
        json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
        if len(sys.argv) > 2
        else _fetch_json(_GAME_URL)
    )
    buildings: dict[str, Any] = game_raw["buildingsData"]

    merged: dict[str, Any] = {}
    for class_name, data in buildings.items():
        entry: dict[str, Any] = {
            "name": data.get("name"),
            "category": data.get("category"),
            "color": data.get("mapColor"),
            "opacity": data.get("mapOpacity"),
            "weight": data.get("mapWeight"),
            "width": data.get("width"),
            "length": data.get("length"),
        }
        merged[class_name] = {k: v for k, v in entry.items() if v is not None}

    outlines = 0
    for full_path, model in models_raw.items():
        class_name = _short_class(full_path)
        entry = merged.setdefault(class_name, {})
        if model.get("scale") is not None:
            entry["scale"] = model["scale"]
        forms = []
        for form in model.get("forms", []):
            trimmed: dict[str, Any] = {"points": form["points"]}
            if form.get("holes"):
                trimmed["holes"] = form["holes"]
            forms.append(trimmed)
        if forms:
            entry["forms"] = forms
            outlines += 1

    _OUT.parent.mkdir(parents=True, exist_ok=True)
    _OUT.write_text(json.dumps(merged, separators=(",", ":")), encoding="utf-8")
    size_kb = _OUT.stat().st_size / 1024
    print(
        f"Wrote {_OUT.relative_to(_REPO)}: {len(merged)} buildings, "
        f"{outlines} with detailed outlines ({size_kb:.0f} KiB)"
    )


if __name__ == "__main__":
    build()
