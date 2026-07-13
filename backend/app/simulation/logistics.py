"""Simulated logistics provider: a seeded network with wandering trains.

A curated mid-game network (belts, a pipe, a truck route, a drone route, and a
rail line) consistent with the world-map factories/stations. Trains ping-pong
along their line each tick. Replaced by the FRM connector in Phase 11.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.logistics.analysis import summarize
from app.logistics.data import tier_rate
from app.schemas.logistics import (
    LogisticsNode,
    LogisticsRoute,
    LogisticsSnapshot,
    TrainInfo,
)
from app.schemas.world import Position

# (id, name, type, x, y) — aligned with SimulatedWorldProvider features.
_NODES: list[tuple[str, str, str, float, float]] = [
    ("iron-works", "Iron Works", "factory", -70000, 149000),
    ("copper-basin", "Copper Basin", "factory", -61000, 141500),
    ("concrete-plant", "Concrete Plant", "factory", -21000, 123000),
    ("oil-outpost", "Oil Outpost", "factory", 152000, -38000),
    ("central-station", "Central Station", "station", -40000, 90000),
    ("northern-freight", "Northern Freight", "station", 5000, -88000),
    ("drone-port-hq", "HQ Drone Port", "port", -68000, 147500),
]

# (id, name, mode, tier, item, throughput, from, to)
_ROUTES: list[tuple[str, str, str, str, str, float, str, str]] = [
    ("r-iron-belt", "Iron Ore Feed", "belt", "belt-mk5", "iron-ore", 600,
     "iron-works", "central-station"),
    ("r-copper-belt", "Copper Ingot Line", "belt", "belt-mk3", "copper-ingot", 240,
     "copper-basin", "central-station"),
    ("r-plate-belt", "Iron Plate Overflow", "belt", "belt-mk2", "iron-plate", 150,
     "iron-works", "copper-basin"),
    ("r-oil-pipe", "Crude Oil Pipe", "pipe", "pipe-mk2", "crude-oil", 540,
     "oil-outpost", "northern-freight"),
    ("r-concrete-truck", "Concrete Haul", "truck", "truck", "concrete", 180,
     "concrete-plant", "central-station"),
    ("r-drone-parts", "Parts Drone Link", "drone", "drone", "reinforced-iron-plate", 60,
     "drone-port-hq", "northern-freight"),
    ("r-main-rail", "Main Rail Line", "train", "electric-locomotive", "iron-ingot", 480,
     "central-station", "northern-freight"),
]

# Non-belt/pipe nominal capacities (per minute) — belts/pipes use their tier rate.
_MODE_CAPACITY = {"truck": 240.0, "drone": 90.0, "train": 600.0}


def _capacity(mode: str, tier: str) -> float:
    return tier_rate().get(tier, _MODE_CAPACITY.get(mode, 1.0))


@dataclass
class _Train:
    """Mutable simulated train: progress ``t`` in [0, 1] along ``line``."""

    id: str
    name: str
    line: str
    t: float
    direction: float


class SimulatedLogisticsProvider:
    """A static network whose trains advance along the rail line each tick."""

    def __init__(self) -> None:
        self._nodes = [
            LogisticsNode(id=i, name=n, type=ntype, position=Position(x=x, y=y))
            for i, n, ntype, x, y in _NODES
        ]
        self._pos = {n.id: n.position for n in self._nodes}
        self._routes = [
            LogisticsRoute(
                id=rid,
                name=name,
                mode=mode,
                tier=tier,
                item=item,
                throughput_per_min=throughput,
                capacity_per_min=_capacity(mode, tier),
                from_node=src,
                to_node=dst,
            )
            for rid, name, mode, tier, item, throughput, src, dst in _ROUTES
        ]
        self._trains = [
            _Train("train-1", "Freight 01", "r-main-rail", 0.0, 1.0),
            _Train("train-2", "Freight 02", "r-main-rail", 0.6, -1.0),
        ]

    def _train_position(self, line: str, t: float) -> Position:
        route = next(r for r in self._routes if r.id == line)
        a, b = self._pos[route.from_node], self._pos[route.to_node]
        return Position(x=a.x + (b.x - a.x) * t, y=a.y + (b.y - a.y) * t)

    def snapshot(self) -> LogisticsSnapshot:
        """Advance trains one tick and return the network state."""
        trains: list[TrainInfo] = []
        for train in self._trains:
            train.t += 0.05 * train.direction
            if train.t >= 1.0:
                train.t, train.direction = 1.0, -1.0
            elif train.t <= 0.0:
                train.t, train.direction = 0.0, 1.0
            route = next(r for r in self._routes if r.id == train.line)
            trains.append(
                TrainInfo(
                    id=train.id,
                    name=train.name,
                    line=train.line,
                    position=self._train_position(train.line, train.t),
                    loaded_item=route.item,
                )
            )
        return LogisticsSnapshot(
            generated_at=datetime.now(UTC),
            source="simulation",
            nodes=list(self._nodes),
            routes=list(self._routes),
            trains=trains,
            summary=summarize(self._nodes, self._routes),
        )
