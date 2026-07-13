"""Tests for the blueprint library: CRUD, filtering, stats, import/export."""

from __future__ import annotations

from httpx import AsyncClient


async def _create(client: AsyncClient, **overrides: object) -> dict:
    body = {
        "name": "Smelter stack",
        "category": "smelting",
        "tags": ["iron", "starter"],
        "data": {"kind": "layout", "placements": []},
    }
    body.update(overrides)
    resp = await client.post("/api/v1/blueprints", json=body)
    assert resp.status_code == 201
    return resp.json()


async def test_blueprint_crud(client: AsyncClient) -> None:
    created = await _create(client)
    bid = created["id"]
    assert created["category"] == "smelting"
    assert created["data"]["kind"] == "layout"

    fetched = (await client.get(f"/api/v1/blueprints/{bid}")).json()
    assert fetched["tags"] == ["iron", "starter"]

    updated = await client.put(
        f"/api/v1/blueprints/{bid}", json={"favorite": True, "name": "Smelter stack v2"}
    )
    assert updated.status_code == 200
    assert updated.json()["favorite"] is True
    assert updated.json()["name"] == "Smelter stack v2"
    # Unset fields are preserved.
    assert updated.json()["category"] == "smelting"

    deleted = await client.delete(f"/api/v1/blueprints/{bid}")
    assert deleted.status_code == 204
    assert (await client.get(f"/api/v1/blueprints/{bid}")).status_code == 404


async def test_blueprint_filtering(client: AsyncClient) -> None:
    await _create(client, name="A", category="smelting", tags=["iron"], favorite=True)
    await _create(client, name="B", category="power", tags=["coal"])
    await _create(client, name="Copper C", category="smelting", tags=["copper"])

    smelting = (await client.get("/api/v1/blueprints?category=smelting")).json()
    assert {b["name"] for b in smelting} == {"A", "Copper C"}

    coal = (await client.get("/api/v1/blueprints?tag=coal")).json()
    assert [b["name"] for b in coal] == ["B"]

    favs = (await client.get("/api/v1/blueprints?favorite=true")).json()
    assert [b["name"] for b in favs] == ["A"]

    search = (await client.get("/api/v1/blueprints?q=copper")).json()
    assert [b["name"] for b in search] == ["Copper C"]

    # Summaries omit the payload body.
    assert "data" not in smelting[0]


async def test_blueprint_stats(client: AsyncClient) -> None:
    await _create(client, name="A", category="smelting", tags=["iron"], favorite=True)
    await _create(client, name="B", category="power", tags=["coal", "iron"])
    body = (await client.get("/api/v1/blueprints/stats")).json()
    assert body["total"] == 2
    assert body["favorites"] == 1
    assert body["by_category"] == {"smelting": 1, "power": 1}
    assert body["by_tag"]["iron"] == 2


async def test_blueprint_export_import_roundtrip(client: AsyncClient) -> None:
    created = await _create(client, name="Exportable", data={"kind": "recipe", "item": "cable"})
    exported = (await client.get(f"/api/v1/blueprints/{created['id']}/export")).json()
    assert exported["name"] == "Exportable"
    assert "id" not in exported

    imported = await client.post("/api/v1/blueprints/import", json=exported)
    assert imported.status_code == 201
    new_bp = imported.json()
    assert new_bp["id"] != created["id"]
    assert new_bp["data"] == {"kind": "recipe", "item": "cable"}


async def test_blueprint_404(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/blueprints/999999")).status_code == 404
    assert (await client.delete("/api/v1/blueprints/999999")).status_code == 404
