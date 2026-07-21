"""Full in-game item catalogue for the admin spawn picker.

Loads ``database/data/item_catalog.json`` (generated from the game's Docs.json by
``scripts/build_item_catalog.py``) once and caches it. Unlike the production
planner's ``items.json`` seed, this covers every giveable item and is keyed by the
game ``Desc_*_C`` class name the bridge resolves when spawning.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.schemas.admin import SpawnItemInfo

_CATALOG_FILE = Path(__file__).resolve().parents[3] / "database" / "data" / "item_catalog.json"


@lru_cache(maxsize=1)
def load_item_catalog() -> tuple[SpawnItemInfo, ...]:
    """Return every in-game item, sorted by category then name (file order)."""
    data = json.loads(_CATALOG_FILE.read_text(encoding="utf-8"))
    return tuple(SpawnItemInfo(**item) for item in data["items"])
