"""Tests for the game-data endpoint and building loader."""

from __future__ import annotations

from httpx import AsyncClient

from app.planner.gamedata import get_building, load_buildings


def test_load_buildings_annotates_costs() -> None:
    buildings = load_buildings()
    assert buildings, "expected seed buildings"
    smelter = get_building("smelter")
    assert smelter.power_mw == 4
    assert smelter.footprint.width == 6
    assert smelter.build_cost == {"iron-rod": 5, "wire": 8}


def test_get_building_unknown_raises() -> None:
    from app.errors import NotFoundError

    try:
        get_building("nope")
    except NotFoundError:
        return
    raise AssertionError("expected NotFoundError")


async def test_gamedata_buildings_endpoint(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/gamedata/buildings")
    assert resp.status_code == 200
    ids = {b["id"] for b in resp.json()}
    assert {"smelter", "constructor", "manufacturer"} <= ids
