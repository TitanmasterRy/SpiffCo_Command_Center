"""Tests for the world snapshot and custom-marker CRUD."""

from __future__ import annotations

from httpx import AsyncClient

from app.simulation.world import SimulatedWorldProvider


async def test_world_snapshot(client: AsyncClient) -> None:
    response = await client.get("/api/v1/world")
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "simulation"
    assert len(body["players"]) == 2
    types = {f["type"] for f in body["features"]}
    assert {
        "factory",
        "power_plant",
        "train_station",
        "resource_node",
        "artifact",
        "collectible",
        "wreck",
    } <= types


async def test_pickup_and_node_states(client: AsyncClient) -> None:
    features = (await client.get("/api/v1/world")).json()["features"]
    pickups = [f for f in features if f["type"] in {"artifact", "collectible", "wreck"}]
    nodes = [f for f in features if f["type"] == "resource_node"]
    assert pickups and nodes
    # Every pickup carries a collected flag; every node an occupied flag.
    assert all(isinstance(f["collected"], bool) for f in pickups)
    assert all(isinstance(f["occupied"], bool) for f in nodes)
    # Simulated save has both occupied and free nodes.
    assert {n["occupied"] for n in nodes} == {True, False}
    # Infrastructure carries neither flag.
    factory = next(f for f in features if f["type"] == "factory")
    assert factory["collected"] is None and factory["occupied"] is None


async def test_marker_crud(client: AsyncClient) -> None:
    created = await client.post(
        "/api/v1/world/markers",
        json={"name": "Future nuclear site", "position": {"x": 1000, "y": -2000, "z": 300}},
    )
    assert created.status_code == 201
    marker = created.json()
    assert marker["name"] == "Future nuclear site"
    assert marker["color"].startswith("#")

    listing = await client.get("/api/v1/world/markers")
    assert any(m["id"] == marker["id"] for m in listing.json())

    deleted = await client.delete(f"/api/v1/world/markers/{marker['id']}")
    assert deleted.status_code == 204
    missing = await client.delete(f"/api/v1/world/markers/{marker['id']}")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "not_found"


async def test_marker_validation(client: AsyncClient) -> None:
    bad = await client.post(
        "/api/v1/world/markers",
        json={"name": "", "position": {"x": 0, "y": 0}, "color": "red"},
    )
    assert bad.status_code == 422
    assert bad.json()["error"]["code"] == "validation_failed"


def test_players_move_between_snapshots() -> None:
    provider = SimulatedWorldProvider(seed=5)
    first = provider.snapshot()
    second = provider.snapshot()
    assert first.players[0].position.x != second.players[0].position.x
    assert first.features == second.features  # static features stay put


async def test_refresh_publishes_features_only_on_change() -> None:
    from datetime import UTC, datetime

    from app.schemas.world import MapFeature, Position, WorldSnapshot
    from app.services.event_bus import EventBus
    from app.world.service import WorldService

    def snapshot(collected: bool) -> WorldSnapshot:
        return WorldSnapshot(
            generated_at=datetime.now(tz=UTC),
            source="simulation",
            players=[],
            features=[
                MapFeature(
                    id="artifact-1",
                    type="artifact",
                    name="Somersloop",
                    position=Position(x=0, y=0, z=0),
                    collected=collected,
                )
            ],
        )

    class Provider:
        def __init__(self) -> None:
            self.collected = False

        def snapshot(self) -> WorldSnapshot:
            return snapshot(self.collected)

    bus = EventBus()
    subscription = bus.subscribe("world.features")
    provider = Provider()
    service = WorldService(provider, bus)

    await service.refresh()  # first refresh always publishes
    first = await subscription.get()
    assert first.payload[0]["collected"] is False

    await service.refresh()  # unchanged features -> no publish
    provider.collected = True
    await service.refresh()  # collected flipped -> publish
    second = await subscription.get()
    assert second.payload[0]["collected"] is True
