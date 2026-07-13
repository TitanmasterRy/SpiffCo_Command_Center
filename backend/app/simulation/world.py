"""Simulated world provider: static features + wandering players.

Resource nodes are loaded from ``database/data/resource_nodes.json`` when the
file is available (source tree / mounted volume); other features are a curated
mid-game set. Replaced by the FRM connector in Phase 11.
"""

from __future__ import annotations

import json
import logging
import random
from datetime import datetime, timezone
from pathlib import Path

from app.schemas.world import MapFeature, PlayerInfo, Position, WorldSnapshot

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parents[3] / "database" / "data"
_NODES_FILE = _DATA_DIR / "resource_nodes.json"
_COLLECTIBLES_FILE = _DATA_DIR / "collectibles.json"

# Simulated save state: nodes with an extractor installed.
_OCCUPIED_NODES = {"iron-grassfields-01", "limestone-rockydesert-01"}

_STATIC_FEATURES: list[tuple[str, str, str, float, float]] = [
    # (id, type, name, x, y)
    ("iron-works", "factory", "Iron Works", -70000, 149000),
    ("copper-basin", "factory", "Copper Basin", -61000, 141500),
    ("concrete-plant", "factory", "Concrete Plant", -21000, 123000),
    ("oil-outpost", "factory", "Oil Outpost", 152000, -38000),
    ("coal-plant-north", "power_plant", "Coal Plant North", 9500, -93000),
    ("bio-burners-hub", "power_plant", "Biomass Hub", -66000, 146000),
    ("central-station", "train_station", "Central Station", -40000, 90000),
    ("northern-freight", "train_station", "Northern Freight", 5000, -88000),
    ("drone-port-hq", "drone_port", "HQ Drone Port", -68000, 147500),
    ("truck-stop-desert", "truck_station", "Desert Truck Stop", -18000, 118000),
]


def _load_resource_nodes() -> list[MapFeature]:
    """Read node features from the shared game-data file; empty list if absent."""
    try:
        data = json.loads(_NODES_FILE.read_text(encoding="utf-8"))
    except OSError:
        logger.warning("resource_nodes.json not found at %s; map will omit nodes", _NODES_FILE)
        return []
    return [
        MapFeature(
            id=node["id"],
            type="resource_node",
            name=f"{node['resource']} ({node['purity']})",
            position=Position(**node["position"]),
            meta={"resource": node["resource"], "purity": node["purity"], "region": node["region"]},
            occupied=node["id"] in _OCCUPIED_NODES,
        )
        for node in data["nodes"]
    ]


def _load_collectibles(rng: random.Random) -> list[MapFeature]:
    """Read pickups (artifacts, food, wrecks) from the shared game-data file.

    Collected state is per-save; the simulation marks roughly 40% as collected
    (stable for a given seed).
    """
    try:
        data = json.loads(_COLLECTIBLES_FILE.read_text(encoding="utf-8"))
    except OSError:
        logger.warning("collectibles.json not found at %s; map will omit pickups", _COLLECTIBLES_FILE)
        return []
    return [
        MapFeature(
            id=entry["id"],
            type=entry["category"],
            name=entry["name"],
            position=Position(**entry["position"]),
            meta=entry.get("meta", {}),
            collected=rng.random() < 0.4,
        )
        for entry in data["collectibles"]
    ]


class SimulatedWorldProvider:
    """Static features plus players random-walking near the starter factories."""

    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)
        self._features = (
            [
                MapFeature(id=fid, type=ftype, name=name, position=Position(x=x, y=y))  # type: ignore[arg-type]
                for fid, ftype, name, x, y in _STATIC_FEATURES
            ]
            + _load_resource_nodes()
            + _load_collectibles(self._rng)
        )
        self._players = {
            "player-1": Position(x=-69000, y=148000, z=1500),
            "player-2": Position(x=-20000, y=121000, z=6000),
        }

    def snapshot(self) -> WorldSnapshot:
        """Advance player positions one tick and return the world state."""
        for pos in self._players.values():
            pos.x += self._rng.uniform(-1500, 1500)
            pos.y += self._rng.uniform(-1500, 1500)
        return WorldSnapshot(
            generated_at=datetime.now(timezone.utc),
            source="simulation",
            players=[
                PlayerInfo(id=pid, name=pid.replace("-", " ").title(), position=pos.model_copy())
                for pid, pos in self._players.items()
            ],
            features=list(self._features),
        )
