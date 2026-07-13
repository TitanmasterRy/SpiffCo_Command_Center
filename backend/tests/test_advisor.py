"""Tests for the AI advisor: detection rules, ranking, and the endpoint."""

from __future__ import annotations

from datetime import UTC, datetime

from httpx import AsyncClient

from app.advisors.engine import build_findings
from app.schemas.dashboard import (
    DashboardSnapshot,
    FactoryStatus,
    MachineSummary,
    PowerStats,
    ProductionStat,
    StorageLevel,
)
from app.schemas.logistics import LogisticsRoute, LogisticsSnapshot, LogisticsSummary


def _dashboard(**overrides: object) -> DashboardSnapshot:
    base: dict = dict(
        generated_at=datetime.now(UTC),
        source="simulation",
        power=PowerStats(
            produced_mw=120,
            consumed_mw=80,
            capacity_mw=200,
            battery_percent=0.6,
            battery_capacity_mwh=100,
        ),
        machines=MachineSummary(total=10, running=10, idle=0, unpowered=0),
        factories=[
            FactoryStatus(
                id="f1", name="Iron Works", status="ok", efficiency=1.0,
                machines=MachineSummary(total=5, running=5),
            )
        ],
        production=[
            ProductionStat(
                item="iron-plate", name="Iron Plate", current_per_min=20, target_per_min=20
            )
        ],
        storage=[StorageLevel(item="iron-plate", name="Iron Plate", stored=100, capacity=1000)],
        alerts=[],
    )
    base.update(overrides)
    return DashboardSnapshot(**base)


def _logistics(routes: list[LogisticsRoute] | None = None) -> LogisticsSnapshot:
    routes = routes or []
    return LogisticsSnapshot(
        generated_at=datetime.now(UTC),
        source="simulation",
        nodes=[],
        routes=routes,
        trains=[],
        summary=LogisticsSummary(route_count=len(routes), node_count=0),
    )


def _route(over: bool) -> LogisticsRoute:
    return LogisticsRoute(
        id="r1", name="Iron Feed", mode="belt", tier="belt-mk1", item="iron-ore",
        throughput_per_min=150 if over else 30,
        capacity_per_min=120,
        from_node="a", to_node="b",
    )


def test_healthy_state_returns_single_info() -> None:
    findings = build_findings(_dashboard(), _logistics())
    assert len(findings) == 1
    assert findings[0].severity == "info"
    assert findings[0].category == "general"


def test_detects_power_shortfall() -> None:
    dash = _dashboard(
        power=PowerStats(
            produced_mw=190, consumed_mw=210, capacity_mw=200,
            battery_percent=0.5, battery_capacity_mwh=100,
        )
    )
    findings = build_findings(dash, _logistics())
    power = next(f for f in findings if f.id == "power:capacity")
    assert power.severity == "critical"
    # Consumption > production also flags a draining battery.
    assert any(f.id == "power:battery" for f in findings)


def test_detects_machines_factory_production_storage_logistics() -> None:
    dash = _dashboard(
        machines=MachineSummary(total=10, running=6, idle=1, unpowered=3),
        factories=[
            FactoryStatus(
                id="f1", name="Iron Works", status="error", efficiency=0.0,
                machines=MachineSummary(total=5, running=0),
            )
        ],
        production=[
            ProductionStat(
                item="iron-plate", name="Iron Plate", current_per_min=5, target_per_min=20
            )
        ],
        storage=[StorageLevel(item="screw", name="Screw", stored=980, capacity=1000)],
    )
    findings = build_findings(dash, _logistics([_route(over=True)]))
    ids = {f.id for f in findings}
    assert "machines:unpowered" in ids
    assert "factory:f1" in ids
    assert "production:iron-plate" in ids
    assert "storage:screw" in ids
    assert "logistics:r1" in ids
    # Ranked with the critical factory outage first.
    assert findings[0].severity == "critical"
    # Every finding carries an explanation and a suggestion.
    assert all(f.explanation and f.suggestion for f in findings)


async def test_advisor_endpoint(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/advisor")
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "simulation"
    assert isinstance(body["findings"], list) and body["findings"]
    assert "counts" in body
    # Findings are ranked: no info appears before a warning/critical.
    severities = [f["severity"] for f in body["findings"]]
    rank = {"critical": 0, "warning": 1, "info": 2}
    assert severities == sorted(severities, key=lambda s: rank[s])
