"""Normalize raw FRM payloads into internal schemas.

Pure functions (no I/O) so they can be unit-tested against captured/fixture FRM
JSON. They are deliberately defensive — the FRM mod's field set varies by version
and installed mods — using ``.get`` with sensible fallbacks so a missing field
degrades gracefully instead of raising. Raw FRM shapes never leave this package.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

from app.schemas.dashboard import (
    DashboardSnapshot,
    FactoryStatus,
    MachineSummary,
    PowerStats,
    ProductionStat,
    StorageLevel,
)
from app.schemas.logistics import (
    LogisticsNode,
    LogisticsSnapshot,
    TrainInfo,
)
from app.schemas.logistics import (
    LogisticsSummary as LogSummary,
)
from app.schemas.world import MapFeature, PlayerInfo, Position, WorldSnapshot

Raw = dict[str, Any]


def _num(value: Any, default: float = 0.0) -> float:
    """Coerce a value to float, falling back to *default*."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _location(entry: Raw) -> Position:
    """Read a FRM ``location`` object into a :class:`Position` (cm)."""
    loc = entry.get("location") or entry.get("Location") or {}
    return Position(x=_num(loc.get("x")), y=_num(loc.get("y")), z=_num(loc.get("z")))


def _slug(name: str) -> str:
    """Stable-ish id slug from a display name."""
    return "-".join(name.lower().split()) or "unknown"


def normalize_power(circuits: Iterable[Raw]) -> PowerStats:
    """Aggregate FRM power circuits into grid-wide :class:`PowerStats`."""
    produced = consumed = capacity = 0.0
    battery_capacity = battery_stored = 0.0
    fuse = False
    for circuit in circuits:
        produced += _num(circuit.get("PowerProduction"))
        consumed += _num(circuit.get("PowerConsumed"))
        capacity += _num(circuit.get("PowerCapacity"))
        cap_mwh = _num(circuit.get("BatteryCapacity"))
        battery_capacity += cap_mwh
        battery_stored += cap_mwh * _num(circuit.get("BatteryPercent")) / 100.0
        fuse = fuse or bool(circuit.get("FuseTriggered"))
    percent = (battery_stored / battery_capacity) if battery_capacity > 0 else 0.0
    return PowerStats(
        produced_mw=round(produced, 3),
        consumed_mw=round(consumed, 3),
        capacity_mw=round(capacity, 3),
        battery_percent=round(min(1.0, max(0.0, percent)), 4),
        battery_capacity_mwh=round(battery_capacity, 3),
        fuse_triggered=fuse,
    )


def _factory_groups(buildings: Iterable[Raw]) -> tuple[list[FactoryStatus], MachineSummary]:
    """Group FRM production buildings by class name into factory summaries."""
    groups: dict[str, dict[str, float]] = {}
    for b in buildings:
        name = str(b.get("Name") or b.get("building") or "Building")
        g = groups.setdefault(name, {"total": 0, "running": 0, "unpowered": 0, "eff": 0.0})
        g["total"] += 1
        productivity = _num(b.get("productivity"), _num(b.get("ManuSpeed")))
        producing = bool(b.get("IsProducing", productivity > 0))
        powered = bool(b.get("IsConfigured", True)) and _num(
            (b.get("powerInfo") or {}).get("PowerConsumed"), 1.0
        ) >= 0
        if not powered:
            g["unpowered"] += 1
        elif producing:
            g["running"] += 1
        g["eff"] += productivity / 100.0 if productivity > 1 else productivity

    factories: list[FactoryStatus] = []
    totals = MachineSummary()
    for name, g in groups.items():
        total = int(g["total"])
        running = int(g["running"])
        unpowered = int(g["unpowered"])
        idle = max(0, total - running - unpowered)
        eff = g["eff"] / total if total else 0.0
        status = "ok" if eff >= 0.9 else "warn" if eff >= 0.6 else "error"
        machines = MachineSummary(total=total, running=running, idle=idle, unpowered=unpowered)
        factories.append(
            FactoryStatus(
                id=_slug(name),
                name=name,
                status=status,
                efficiency=min(1.0, eff),
                machines=machines,
            )
        )
        totals = MachineSummary(
            total=totals.total + total,
            running=totals.running + running,
            idle=totals.idle + idle,
            unpowered=totals.unpowered + unpowered,
        )
    return factories, totals


def _production(buildings: Iterable[Raw]) -> list[ProductionStat]:
    """Aggregate current/max output per item across all buildings."""
    current: dict[str, float] = {}
    target: dict[str, float] = {}
    for b in buildings:
        for out in b.get("production", []) or []:
            item = str(out.get("Name") or out.get("item") or "item")
            cur = _num(out.get("CurrentProd"))
            current[item] = current.get(item, 0.0) + cur
            target[item] = target.get(item, 0.0) + _num(out.get("MaxProd"), cur)
    return [
        ProductionStat(
            item=_slug(item),
            name=item,
            current_per_min=round(current[item], 3),
            target_per_min=round(target.get(item, current[item]), 3),
        )
        for item in current
    ]


def _storage(inventory: Iterable[Raw]) -> list[StorageLevel]:
    """Storage levels from a FRM world/storage inventory payload."""
    levels: list[StorageLevel] = []
    for entry in inventory:
        name = str(entry.get("Name") or entry.get("item") or "item")
        levels.append(
            StorageLevel(
                item=_slug(name),
                name=name,
                stored=_num(entry.get("Amount") or entry.get("stored")),
                capacity=_num(entry.get("MaxAmount") or entry.get("capacity"), 0.0),
            )
        )
    return levels


def normalize_dashboard(
    power_raw: Iterable[Raw],
    factory_raw: Iterable[Raw],
    inventory_raw: Iterable[Raw] | None = None,
) -> DashboardSnapshot:
    """Build a dashboard snapshot from FRM power/factory/inventory payloads."""
    factory_list = list(factory_raw)
    factories, machines = _factory_groups(factory_list)
    return DashboardSnapshot(
        generated_at=datetime.now(UTC),
        source="frm",
        power=normalize_power(power_raw),
        machines=machines,
        factories=factories,
        production=_production(factory_list),
        storage=_storage(inventory_raw or []),
        alerts=[],
    )


_NODE_TYPE_MAP = {
    "factory": "factory",
    "trainstation": "train_station",
    "dronestation": "drone_port",
    "truckstation": "truck_station",
}


def normalize_world(
    players_raw: Iterable[Raw],
    factory_raw: Iterable[Raw],
    nodes_raw: Iterable[Raw],
) -> WorldSnapshot:
    """Build a world snapshot from FRM players / factories / resource nodes."""
    players = [
        PlayerInfo(
            id=_slug(str(p.get("Name") or f"player-{i}")),
            name=str(p.get("Name") or f"Player {i}"),
            position=_location(p),
            online=True,
        )
        for i, p in enumerate(players_raw, start=1)
    ]
    features: list[MapFeature] = []
    for b in factory_raw:
        name = str(b.get("Name") or "Factory")
        features.append(
            MapFeature(id=_slug(name), type="factory", name=name, position=_location(b))
        )
    for node in nodes_raw:
        name = str(node.get("Name") or node.get("ResourceForm") or "Node")
        purity = str(node.get("Purity") or "normal").lower()
        occupied = bool(node.get("Exploited") or node.get("Occupied"))
        features.append(
            MapFeature(
                id=_slug(f"{name}-{node.get('ID', len(features))}"),
                type="resource_node",
                name=name,
                position=_location(node),
                meta={"resource": _slug(name), "purity": purity},
                occupied=occupied,
            )
        )
    return WorldSnapshot(
        generated_at=datetime.now(UTC), source="frm", players=players, features=features
    )


def normalize_logistics(
    stations_raw: Iterable[Raw], trains_raw: Iterable[Raw]
) -> LogisticsSnapshot:
    """Build a logistics snapshot from FRM train stations and trains."""
    nodes = [
        LogisticsNode(
            id=_slug(str(s.get("Name") or f"station-{i}")),
            name=str(s.get("Name") or f"Station {i}"),
            type="station",
            position=_location(s),
        )
        for i, s in enumerate(stations_raw, start=1)
    ]
    trains = [
        TrainInfo(
            id=_slug(str(t.get("Name") or f"train-{i}")),
            name=str(t.get("Name") or f"Train {i}"),
            line=str(t.get("TrainStation") or "unknown"),
            position=_location(t),
            loaded_item=None,
        )
        for i, t in enumerate(trains_raw, start=1)
    ]
    return LogisticsSnapshot(
        generated_at=datetime.now(UTC),
        source="frm",
        nodes=nodes,
        routes=[],  # belt/pipe throughput is not exposed by FRM; rail routes TBD
        trains=trains,
        summary=LogSummary(route_count=0, node_count=len(nodes)),
    )
