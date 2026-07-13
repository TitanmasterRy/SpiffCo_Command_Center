"""Turn a :class:`ParsedSave` into normalized snapshots + a summary.

The three providers satisfy the same synchronous ``snapshot()`` protocols as the
simulated and FRM providers, so ``GameStateService`` / ``WorldService`` /
``LogisticsService`` run unchanged when a save is the active source.

To stay DRY we reshape the parsed save into the same dict shapes the FRM
normalizers already consume and call them with ``source="save"``. A static save
exposes no positions or live rates, so the world/logistics snapshots are
deliberately sparse and the dashboard's power figures are labelled estimates.
"""

from __future__ import annotations

from app.connectors.frm.normalize import (
    normalize_dashboard,
    normalize_logistics,
    normalize_world,
)
from app.offline.building_map import lookup
from app.offline.save_parser import ParsedSave
from app.schemas.dashboard import DashboardSnapshot
from app.schemas.logistics import LogisticsSnapshot
from app.schemas.offline import BuildingCount, SaveSummary
from app.schemas.world import WorldSnapshot

# Guard against a pathological save inflating the synthetic factory-dict list.
_MAX_FACTORY_DICTS = 50_000
# Nominal energy stored per Power Storage unit (MWh).
_BATTERY_MWH_EACH = 100.0


class SaveDataSource:
    """Pre-computes normalized snapshots + a summary from a parsed save (once)."""

    def __init__(self, parsed: ParsedSave) -> None:
        self._parsed = parsed
        self._catalogued = [
            (cls, spec, count)
            for cls, count in parsed.building_counts.items()
            if (spec := lookup(cls)) is not None
        ]
        self._dashboard = self._build_dashboard()
        self._world = normalize_world([], [], [], source="save")
        self._logistics = normalize_logistics([], [], source="save")
        self._summary = self._build_summary()

    # -- provider protocol -------------------------------------------------
    def dashboard(self) -> DashboardSnapshot:
        return self._dashboard

    def world(self) -> WorldSnapshot:
        return self._world

    def logistics(self) -> LogisticsSnapshot:
        return self._logistics

    def summary(self) -> SaveSummary:
        return self._summary

    # -- construction ------------------------------------------------------
    def _build_dashboard(self) -> DashboardSnapshot:
        factory_dicts: list[dict[str, object]] = []
        capacity = consumption = battery_capacity = 0.0
        for _cls, spec, count in self._catalogued:
            if spec.category == "generator":
                capacity += spec.power_mw * count
            elif spec.category == "power_storage":
                battery_capacity += _BATTERY_MWH_EACH * count
            elif spec.category in ("production", "extraction"):
                consumption += spec.power_mw * count
                for _ in range(min(count, _MAX_FACTORY_DICTS - len(factory_dicts))):
                    factory_dicts.append(
                        {"Name": spec.name, "IsProducing": True, "productivity": 100}
                    )

        circuit = {
            "PowerProduction": min(consumption, capacity),
            "PowerConsumed": consumption,
            "PowerCapacity": capacity,
            "BatteryCapacity": battery_capacity,
            "BatteryPercent": 50.0 if battery_capacity > 0 else 0.0,
        }
        return normalize_dashboard([circuit], factory_dicts, [], source="save")

    def _build_summary(self) -> SaveSummary:
        buildings = [
            BuildingCount(
                class_name=cls,
                name=spec.name,
                category=spec.category,
                count=count,
                power_mw=spec.power_mw,
            )
            for cls, spec, count in sorted(
                self._catalogued, key=lambda t: t[2], reverse=True
            )
        ]
        machine_count = sum(
            c for _cls, s, c in self._catalogued if s.category in ("production", "extraction")
        )
        generator_count = sum(
            c for _cls, s, c in self._catalogued if s.category == "generator"
        )
        header = self._parsed.header
        return SaveSummary(
            session_name=header.session_name or "Unnamed save",
            map_name=header.map_name,
            build_version=header.build_version,
            play_duration_seconds=header.play_duration_seconds,
            saved_at=header.saved_at,
            total_buildings=sum(c for _cls, _s, c in self._catalogued),
            machine_count=machine_count,
            generator_count=generator_count,
            estimated_power_capacity_mw=round(self._dashboard.power.capacity_mw, 1),
            estimated_power_consumption_mw=round(self._dashboard.power.consumed_mw, 1),
            buildings=buildings,
        )


class SaveGameProvider:
    """Game-state provider backed by a loaded save."""

    def __init__(self, source: SaveDataSource) -> None:
        self._source = source

    def snapshot(self) -> DashboardSnapshot:
        return self._source.dashboard()


class SaveWorldProvider:
    """World provider backed by a loaded save (sparse — no positions in a save)."""

    def __init__(self, source: SaveDataSource) -> None:
        self._source = source

    def snapshot(self) -> WorldSnapshot:
        return self._source.world()


class SaveLogisticsProvider:
    """Logistics provider backed by a loaded save (sparse — no positions)."""

    def __init__(self, source: SaveDataSource) -> None:
        self._source = source

    def snapshot(self) -> LogisticsSnapshot:
        return self._source.logistics()
