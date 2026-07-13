"""Simulated game-state provider.

Generates plausible, slowly-drifting factory telemetry so the dashboard (and
later phases) work with no game attached. Implements the same ``snapshot()``
contract the FRM connector will provide in Phase 11.
"""

from __future__ import annotations

import random
from datetime import datetime, timezone

from app.schemas.dashboard import (
    Alert,
    DashboardSnapshot,
    FactoryStatus,
    MachineSummary,
    PowerStats,
    ProductionStat,
    StorageLevel,
)

_FACTORIES = [
    ("iron-works", "Iron Works", 42),
    ("copper-basin", "Copper Basin", 28),
    ("concrete-plant", "Concrete Plant", 16),
    ("oil-outpost", "Oil Outpost", 24),
]
_PRODUCTION = [
    ("iron-plate", "Iron Plate", 480.0),
    ("iron-rod", "Iron Rod", 360.0),
    ("screw", "Screw", 960.0),
    ("reinforced-iron-plate", "Reinforced Iron Plate", 60.0),
]
_STORAGE = [
    ("iron-plate", "Iron Plate", 2400.0),
    ("concrete", "Concrete", 1800.0),
    ("cable", "Cable", 1200.0),
]
CAPACITY_MW = 1500.0
BATTERY_CAPACITY_MWH = 500.0


def _drift(value: float, lo: float, hi: float, step: float, rng: random.Random) -> float:
    """Random-walk *value* within [lo, hi]."""
    return min(hi, max(lo, value + rng.uniform(-step, step)))


class SimulatedGameProvider:
    """Stateful random-walk simulation of a mid-game save."""

    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)
        self._efficiency = {fid: self._rng.uniform(0.88, 0.99) for fid, _, _ in _FACTORIES}
        self._consumed = 980.0
        self._battery = 0.85
        self._storage = {item: cap * self._rng.uniform(0.3, 0.7) for item, _, cap in _STORAGE}

    def snapshot(self) -> DashboardSnapshot:
        """Advance the simulation one tick and return the current state."""
        rng = self._rng
        self._consumed = _drift(self._consumed, 700, 1400, 40, rng)
        produced = min(CAPACITY_MW, self._consumed * rng.uniform(0.98, 1.06))
        self._battery = _drift(
            self._battery, 0.05, 1.0, 0.02 if produced >= self._consumed else 0.05, rng
        )

        factories: list[FactoryStatus] = []
        totals = MachineSummary()
        for fid, name, count in _FACTORIES:
            eff = self._efficiency[fid] = _drift(self._efficiency[fid], 0.7, 1.0, 0.02, rng)
            idle = round(count * (1 - eff) * 0.7)
            unpowered = rng.choice([0, 0, 0, 1])
            running = count - idle - unpowered
            machines = MachineSummary(total=count, running=running, idle=idle, unpowered=unpowered)
            totals = MachineSummary(
                total=totals.total + count,
                running=totals.running + running,
                idle=totals.idle + idle,
                unpowered=totals.unpowered + unpowered,
            )
            status = "ok" if eff >= 0.9 else "warn" if eff >= 0.75 else "error"
            factories.append(
                FactoryStatus(id=fid, name=name, status=status, efficiency=eff, machines=machines)
            )

        avg_eff = sum(self._efficiency.values()) / len(self._efficiency)
        production = [
            ProductionStat(
                item=item,
                name=name,
                current_per_min=target * avg_eff * rng.uniform(0.97, 1.0),
                target_per_min=target,
            )
            for item, name, target in _PRODUCTION
        ]

        storage = []
        for item, name, cap in _STORAGE:
            self._storage[item] = _drift(self._storage[item], 0, cap, cap * 0.02, rng)
            storage.append(StorageLevel(item=item, name=name, stored=self._storage[item], capacity=cap))

        power = PowerStats(
            produced_mw=produced,
            consumed_mw=self._consumed,
            capacity_mw=CAPACITY_MW,
            battery_percent=self._battery,
            battery_capacity_mwh=BATTERY_CAPACITY_MWH,
        )
        return DashboardSnapshot(
            generated_at=datetime.now(timezone.utc),
            source="simulation",
            power=power,
            machines=totals,
            factories=factories,
            production=production,
            storage=storage,
            alerts=_derive_alerts(power, factories, storage),
        )


def _derive_alerts(
    power: PowerStats, factories: list[FactoryStatus], storage: list[StorageLevel]
) -> list[Alert]:
    """Rule-based alerts from the current state (advisor engine arrives Phase 10)."""
    alerts: list[Alert] = []
    if power.battery_percent < 0.25:
        alerts.append(
            Alert(
                id="power.battery-low",
                severity="critical",
                title="Battery reserves low",
                message=f"Battery at {power.battery_percent:.0%}; consumption may exceed generation.",
                source="power",
            )
        )
    headroom = power.capacity_mw - power.consumed_mw
    if headroom < power.capacity_mw * 0.1:
        alerts.append(
            Alert(
                id="power.headroom-low",
                severity="warning",
                title="Power headroom below 10%",
                message=f"Only {headroom:.0f} MW spare capacity remains.",
                source="power",
            )
        )
    for factory in factories:
        if factory.status != "ok":
            alerts.append(
                Alert(
                    id=f"factory.{factory.id}.efficiency",
                    severity="warning" if factory.status == "warn" else "critical",
                    title=f"{factory.name} below target",
                    message=f"Running at {factory.efficiency:.0%} efficiency "
                    f"({factory.machines.idle} idle, {factory.machines.unpowered} unpowered).",
                    source="factory",
                )
            )
    for level in storage:
        if level.capacity and level.stored / level.capacity > 0.95:
            alerts.append(
                Alert(
                    id=f"storage.{level.item}.full",
                    severity="info",
                    title=f"{level.name} storage nearly full",
                    message=f"{level.stored:.0f}/{level.capacity:.0f} stored.",
                    source="storage",
                )
            )
    return alerts
