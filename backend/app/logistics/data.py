"""Static transport game-data access (belts, pipes, vehicles)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.schemas.logistics import BeltTier, TransportData, VehicleTier

_DATA_DIR = Path(__file__).resolve().parents[3] / "database" / "data"
_TRANSPORT_FILE = _DATA_DIR / "transportation.json"


@lru_cache(maxsize=1)
def load_transport() -> TransportData:
    """The full transport catalog (belts, pipes, vehicles), cached."""
    data = json.loads(_TRANSPORT_FILE.read_text(encoding="utf-8"))
    return TransportData(
        belts=[BeltTier(**b) for b in data["belts"]],
        pipes=[BeltTier(**p) for p in data["pipes"]],
        vehicles=[VehicleTier(**v) for v in data["vehicles"]],
    )


@lru_cache(maxsize=1)
def tier_rate() -> dict[str, float]:
    """Lookup from belt/pipe tier id to its per-minute capacity."""
    transport = load_transport()
    return {t.id: t.rate for t in [*transport.belts, *transport.pipes]}
