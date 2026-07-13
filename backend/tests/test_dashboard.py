"""Tests for the dashboard: snapshot endpoint, simulation, history recording."""

from __future__ import annotations

from httpx import AsyncClient

from app.services.event_bus import EventBus
from app.services.game_state import GameStateService
from app.simulation.provider import SimulatedGameProvider


async def test_snapshot_endpoint(client: AsyncClient) -> None:
    response = await client.get("/api/v1/dashboard")
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "simulation"
    assert body["power"]["capacity_mw"] > 0
    assert body["machines"]["total"] > 0
    assert len(body["factories"]) == 4
    assert len(body["production"]) == 4
    for factory in body["factories"]:
        m = factory["machines"]
        assert m["running"] + m["idle"] + m["unpowered"] == m["total"]


async def test_power_history_endpoint(client: AsyncClient) -> None:
    # Lifespan refreshed once; force a history sample via the service.
    response = await client.get("/api/v1/dashboard/history/power?limit=10")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_simulation_is_deterministic_with_seed() -> None:
    a = SimulatedGameProvider(seed=7).snapshot()
    b = SimulatedGameProvider(seed=7).snapshot()
    assert a.power.consumed_mw == b.power.consumed_mw
    assert [f.efficiency for f in a.factories] == [f.efficiency for f in b.factories]


async def test_refresh_publishes_snapshot() -> None:
    bus = EventBus()
    sub = bus.subscribe("dashboard.*")
    service = GameStateService(SimulatedGameProvider(seed=1), bus)
    await service.refresh()
    event = sub.queue.get_nowait()
    assert event.topic == "dashboard.snapshot"
    assert event.payload["source"] == "simulation"
    assert service.latest.power.capacity_mw > 0


def test_alerts_have_required_fields() -> None:
    snap = SimulatedGameProvider(seed=3).snapshot()
    for alert in snap.alerts:
        assert alert.severity in {"info", "warning", "critical"}
        assert alert.title and alert.message and alert.source
