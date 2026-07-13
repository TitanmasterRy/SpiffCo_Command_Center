"""Static game-data access for the planner (buildings + build costs).

Reads the shared JSON in ``database/data`` and normalizes it into
:class:`~app.schemas.planner.BuildingInfo`. Results are cached with
``functools.lru_cache`` since the files are immutable at runtime; the frontend
gets one source of truth via ``GET /api/v1/gamedata/buildings`` instead of
bundling the JSON.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.errors import NotFoundError
from app.schemas.planner import BuildingInfo, Footprint

_DATA_DIR = Path(__file__).resolve().parents[3] / "database" / "data"
_BUILDINGS_FILE = _DATA_DIR / "buildings.json"
_BUILD_COSTS_FILE = _DATA_DIR / "build_costs.json"


def _load_build_costs() -> dict[str, dict[str, int]]:
    """building id -> {item id: quantity}; empty if the file is missing."""
    try:
        data = json.loads(_BUILD_COSTS_FILE.read_text(encoding="utf-8"))
    except OSError:
        return {}
    return {entry["building"]: dict(entry["cost"]) for entry in data.get("build_costs", [])}


@lru_cache(maxsize=1)
def load_buildings() -> tuple[BuildingInfo, ...]:
    """All production/extraction buildings, cost-annotated, in file order."""
    data = json.loads(_BUILDINGS_FILE.read_text(encoding="utf-8"))
    costs = _load_build_costs()
    return tuple(
        BuildingInfo(
            id=b["id"],
            name=b["name"],
            category=b["category"],
            power_mw=float(b["power_mw"]),
            inputs=int(b["inputs"]),
            outputs=int(b["outputs"]),
            footprint=Footprint(**b["footprint"]),
            build_cost=costs.get(b["id"], {}),
        )
        for b in data["buildings"]
    )


@lru_cache(maxsize=1)
def buildings_by_id() -> dict[str, BuildingInfo]:
    """Lookup map from building id to its :class:`BuildingInfo`."""
    return {b.id: b for b in load_buildings()}


def get_building(building_id: str) -> BuildingInfo:
    """Return a building or raise :class:`NotFoundError`."""
    building = buildings_by_id().get(building_id)
    if building is None:
        raise NotFoundError(f"unknown building {building_id!r}")
    return building
