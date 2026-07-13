"""Tests for the FRM connector: normalization, client caching, and polling.

No live game is required — a fake httpx transport serves captured FRM-shaped
payloads so normalization, caching, and the poll loop are all exercised.
"""

from __future__ import annotations

import httpx
import pytest

from app.config.settings import Settings
from app.connectors.frm import normalize
from app.connectors.frm.client import FrmClient
from app.connectors.frm.connector import ConnectionState, FrmConnector
from app.connectors.frm.providers import FrmGameProvider
from app.errors import UpstreamUnavailableError
from app.services.event_bus import EventBus

FRM_POWER = [
    {"PowerProduction": 600, "PowerConsumed": 500, "PowerCapacity": 900,
     "BatteryCapacity": 100, "BatteryPercent": 80, "FuseTriggered": False},
    {"PowerProduction": 400, "PowerConsumed": 450, "PowerCapacity": 500,
     "BatteryCapacity": 0, "BatteryPercent": 0, "FuseTriggered": False},
]
def _building(name: str, x: int, producing: bool, prod: float, item: str, cur: float, mx: float):
    return {
        "Name": name,
        "location": {"x": x, "y": 200, "z": 0},
        "IsProducing": producing,
        "productivity": prod,
        "production": [{"Name": item, "CurrentProd": cur, "MaxProd": mx}],
    }


FRM_FACTORY = [
    _building("Smelter", 100, True, 100, "Iron Ingot", 30, 30),
    _building("Smelter", 110, False, 0, "Iron Ingot", 0, 30),
    _building("Constructor", 300, True, 50, "Iron Plate", 10, 20),
]
FRM_PLAYER = [{"Name": "Pioneer", "location": {"x": 1, "y": 2, "z": 3}}]
FRM_NODE = [
    {"Name": "Iron Ore", "location": {"x": 5, "y": 6, "z": 0}, "Purity": "Pure", "Exploited": True},
]
FRM_STATION = [{"Name": "Central", "location": {"x": 0, "y": 0, "z": 0}}]
FRM_TRAIN = [
    {"Name": "Freight 1", "location": {"x": 10, "y": 10, "z": 0}, "TrainStation": "Central"},
]

_ROUTES = {
    "getPower": FRM_POWER,
    "getFactory": FRM_FACTORY,
    "getPlayer": FRM_PLAYER,
    "getResourceNode": FRM_NODE,
    "getTrainStation": FRM_STATION,
    "getTrains": FRM_TRAIN,
}


def _ok_transport(counter: dict[str, int] | None = None) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path.lstrip("/")
        if counter is not None:
            counter[path] = counter.get(path, 0) + 1
        return httpx.Response(200, json=_ROUTES.get(path, []))

    return httpx.MockTransport(handler)


def _error_transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "boom"})

    return httpx.MockTransport(handler)


def test_normalize_power_aggregates() -> None:
    power = normalize.normalize_power(FRM_POWER)
    assert power.produced_mw == 1000
    assert power.consumed_mw == 950
    assert power.capacity_mw == 1400
    # 80% of 100 MWh battery / 100 MWh total = 0.8.
    assert power.battery_percent == 0.8
    assert power.fuse_triggered is False


def test_normalize_dashboard_groups_and_production() -> None:
    dash = normalize.normalize_dashboard(FRM_POWER, FRM_FACTORY)
    assert dash.source == "frm"
    smelter = next(f for f in dash.factories if f.id == "smelter")
    assert smelter.machines.total == 2
    assert smelter.machines.running == 1
    items = {p.item: p for p in dash.production}
    assert items["iron-ingot"].current_per_min == 30
    assert items["iron-plate"].target_per_min == 20


def test_normalize_dashboard_frm_1_5_shape() -> None:
    """FRM 1.5.x uses capitalized keys (Productivity, PowerInfo, FuseTriggered).

    Regression guard: reading lowercase ``productivity`` made idle machines
    (Productivity 0, ManuSpeed 100) report 100% efficiency.
    """
    buildings = [
        {  # idle: configured but not producing, 0 productivity
            "Name": "Refinery", "location": {"x": 1, "y": 2, "z": 0},
            "Productivity": 0, "ManuSpeed": 100, "IsProducing": False,
            "IsConfigured": True, "PowerInfo": {"PowerConsumed": 0, "FuseTriggered": False},
            "production": [{"Name": "Plastic", "CurrentProd": 0, "MaxProd": 20}],
        },
        {  # running at full tilt
            "Name": "Refinery", "location": {"x": 3, "y": 4, "z": 0},
            "Productivity": 100, "ManuSpeed": 100, "IsProducing": True,
            "IsConfigured": True, "PowerInfo": {"PowerConsumed": 30, "FuseTriggered": False},
            "production": [{"Name": "Plastic", "CurrentProd": 20, "MaxProd": 20}],
        },
        {  # fuse tripped -> unpowered
            "Name": "Refinery", "location": {"x": 5, "y": 6, "z": 0},
            "Productivity": 0, "ManuSpeed": 100, "IsProducing": False,
            "IsConfigured": True, "PowerInfo": {"PowerConsumed": 0, "FuseTriggered": True},
            "production": [],
        },
    ]
    dash = normalize.normalize_dashboard(FRM_POWER, buildings)
    refinery = next(f for f in dash.factories if f.id == "refinery")
    assert refinery.machines.total == 3
    assert refinery.machines.running == 1
    assert refinery.machines.unpowered == 1
    assert refinery.machines.idle == 1
    # eff = (0 + 1.0 + 0) / 3 ≈ 0.33 — NOT 1.0 from the ManuSpeed fallback bug.
    assert refinery.efficiency == pytest.approx(1 / 3, abs=0.01)


def test_normalize_world_and_logistics() -> None:
    world = normalize.normalize_world(FRM_PLAYER, FRM_FACTORY, FRM_NODE)
    assert world.players[0].name == "Pioneer"
    node = next(f for f in world.features if f.type == "resource_node")
    assert node.occupied is True and node.meta["purity"] == "pure"
    # Purity is surfaced in the display name; the resource slug stays purity-free.
    assert node.name == "Iron Ore (Pure)"
    assert node.meta["resource"] == "iron-ore"


def test_normalize_world_buildings_get_unique_ids_and_meta() -> None:
    """Every building is its own feature: same-class buildings must not collide.

    Regression guard: ids were derived from the name alone, so the two Smelters
    shared one id and rendered as a single marker.
    """
    world = normalize.normalize_world(FRM_PLAYER, FRM_FACTORY, [])
    factories = [f for f in world.features if f.type == "factory"]
    assert len(factories) == 3
    assert len({f.id for f in factories}) == 3  # all distinct
    smelter = factories[0]
    assert smelter.meta["produces"] == "Iron Ingot"


def test_normalize_world_includes_pickups() -> None:
    """Artifacts, power slugs, and drop pods become map features on live data."""
    artifacts = [{"ID": "WAT2_1", "Name": "Mercer Sphere", "location": {"x": 1, "y": 2, "z": 0}}]
    slugs = [{"ID": "C_1", "Name": "Blue Power Slug", "location": {"x": 3, "y": 4, "z": 0}}]
    pods = [
        {"ID": "P_1", "location": {"x": 5, "y": 6, "z": 0}, "Looted": False,
         "RequiredItem": {"Name": "Modular Frame"}},
        {"ID": "P_2", "location": {"x": 7, "y": 8, "z": 0}, "Looted": True},
    ]
    world = normalize.normalize_world(
        FRM_PLAYER, FRM_FACTORY, FRM_NODE,
        artifacts_raw=artifacts, slugs_raw=slugs, drop_pods_raw=pods,
    )
    artifact_names = {f.name for f in world.features if f.type == "artifact"}
    assert {"Mercer Sphere", "Blue Power Slug"} <= artifact_names
    wrecks = [f for f in world.features if f.type == "wreck"]
    assert len(wrecks) == 2
    looted = next(f for f in wrecks if f.id == "wreck-p-2")
    assert looted.collected is True
    unlooted = next(f for f in wrecks if f.id == "wreck-p-1")
    assert unlooted.collected is False and unlooted.meta["requires"] == "Modular Frame"
    logistics = normalize.normalize_logistics(FRM_STATION, FRM_TRAIN)
    assert logistics.nodes[0].name == "Central"
    assert logistics.trains[0].name == "Freight 1"


async def test_client_caches_and_errors() -> None:
    counter: dict[str, int] = {}
    client = FrmClient("http://frm.test", cache_ttl=100, transport=_ok_transport(counter))
    await client.get("getPower")
    await client.get("getPower")  # served from cache
    assert counter["getPower"] == 1
    assert await client.healthy() is True
    await client.aclose()

    bad = FrmClient("http://frm.test", transport=_error_transport())
    with pytest.raises(UpstreamUnavailableError):
        await bad.get("getPower")
    assert await bad.healthy() is False
    await bad.aclose()


async def test_connector_poll_populates_snapshots() -> None:
    settings = Settings(frm_enabled=True, frm_base_url="http://frm.test")
    connector = FrmConnector(
        settings, EventBus(), client=FrmClient("http://frm.test", transport=_ok_transport())
    )
    await connector.poll_once()
    assert connector.state == ConnectionState.CONNECTED
    provider = FrmGameProvider(connector)
    snap = provider.snapshot()
    assert snap.source == "frm"
    assert snap.power.produced_mw == 1000
    assert connector.world_snapshot().players[0].name == "Pioneer"
    await connector.stop()
    assert connector.state == ConnectionState.DISCONNECTED


async def test_connector_start_raises_when_unreachable() -> None:
    settings = Settings(frm_enabled=True, frm_base_url="http://frm.test")
    connector = FrmConnector(
        settings, EventBus(), client=FrmClient("http://frm.test", transport=_error_transport())
    )
    with pytest.raises(UpstreamUnavailableError):
        await connector.start()
    await connector.stop()
