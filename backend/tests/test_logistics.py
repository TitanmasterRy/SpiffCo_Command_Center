"""Tests for logistics: utilization analysis, provider, and API."""

from __future__ import annotations

from httpx import AsyncClient

from app.logistics.analysis import summarize
from app.schemas.logistics import LogisticsNode, LogisticsRoute
from app.schemas.world import Position
from app.simulation.logistics import SimulatedLogisticsProvider


def _route(rid: str, throughput: float, capacity: float, mode: str = "belt") -> LogisticsRoute:
    return LogisticsRoute(
        id=rid,
        name=rid,
        mode=mode,  # type: ignore[arg-type]
        tier="belt-mk1",
        item="iron-ore",
        throughput_per_min=throughput,
        capacity_per_min=capacity,
        from_node="a",
        to_node="b",
    )


def test_route_utilization_and_over_capacity() -> None:
    ok = _route("r1", 60, 120)
    assert ok.utilization == 0.5
    assert ok.over_capacity is False
    hot = _route("r2", 300, 270)
    assert hot.over_capacity is True
    assert hot.utilization > 1


def test_summarize_rolls_up_modes_and_flags() -> None:
    nodes = [
        LogisticsNode(id="a", name="A", type="factory", position=Position(x=0, y=0)),
        LogisticsNode(id="b", name="B", type="station", position=Position(x=1, y=1)),
    ]
    routes = [
        _route("r1", 60, 120, "belt"),
        _route("r2", 300, 270, "belt"),
        _route("r3", 100, 240, "truck"),
    ]
    summary = summarize(nodes, routes)
    assert summary.route_count == 3
    assert summary.node_count == 2
    assert summary.over_capacity_routes == ["r2"]
    assert summary.throughput_by_mode == {"belt": 360.0, "truck": 100.0}
    assert summary.max_utilization > 1


def test_provider_trains_move() -> None:
    provider = SimulatedLogisticsProvider()
    first = provider.snapshot()
    second = provider.snapshot()
    assert len(first.trains) == 2
    assert first.trains[0].position.x != second.trains[0].position.x
    assert first.routes == second.routes  # network is static
    assert first.summary.route_count == len(first.routes)


async def test_logistics_snapshot_endpoint(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/logistics")
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "simulation"
    assert body["nodes"] and body["routes"] and body["trains"]
    # Every route carries a derived utilization; belts/pipes match their tier.
    assert all("utilization" in r for r in body["routes"])
    assert body["summary"]["route_count"] == len(body["routes"])


async def test_gamedata_transport_endpoint(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/gamedata/transport")
    assert resp.status_code == 200
    body = resp.json()
    assert {b["id"] for b in body["belts"]} >= {"belt-mk1", "belt-mk5"}
    assert any(v["id"] == "drone" for v in body["vehicles"])
