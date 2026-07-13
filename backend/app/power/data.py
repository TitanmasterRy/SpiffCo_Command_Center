"""Static power-generator game-data access (`power_buildings.json`)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.schemas.power import PowerBuildingInfo

_DATA_DIR = Path(__file__).resolve().parents[3] / "database" / "data"
_POWER_FILE = _DATA_DIR / "power_buildings.json"


@lru_cache(maxsize=1)
def load_power_buildings() -> tuple[PowerBuildingInfo, ...]:
    """All generators / power storage in file order, cached."""
    data = json.loads(_POWER_FILE.read_text(encoding="utf-8"))
    return tuple(PowerBuildingInfo(**b) for b in data["power_buildings"])
