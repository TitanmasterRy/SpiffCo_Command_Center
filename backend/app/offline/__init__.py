"""Offline mode (Phase 12): read a Satisfactory ``.sav`` file and serve it as a
static data source, so planning and analysis work with no live game.

The save format is intricate and version-dependent. Rather than fully
deserialize every actor's properties (fragile across game versions), this module
takes a deliberately robust subset:

* the **header** (session name, map, build version, play time, save timestamp)
  is parsed exactly — its layout has been stable for many versions;
* the **body** is decompressed by scanning for and inflating its zlib chunks,
  which is independent of the exact chunk-framing of a given version;
* buildings are counted by matching actor **instance names** (``Build_..._C_<id>``)
  in the decompressed body — enough to drive machine counts and a power estimate.

Positions/inventories are intentionally **not** extracted (see
``docs/KNOWN_LIMITATIONS.md``); the save feeds the Dashboard, not the map.
"""

from __future__ import annotations

from app.offline.manager import OfflineManager
from app.offline.provider import SaveGameProvider, SaveLogisticsProvider, SaveWorldProvider
from app.offline.save_parser import ParsedSave, SaveHeader, SaveParseError, parse_save

__all__ = [
    "OfflineManager",
    "ParsedSave",
    "SaveGameProvider",
    "SaveHeader",
    "SaveLogisticsProvider",
    "SaveParseError",
    "SaveWorldProvider",
    "parse_save",
]
