"""Tests for runtime FRM configuration (GET/PUT/test of /settings/frm)."""

from __future__ import annotations

from httpx import AsyncClient


async def test_frm_config_defaults_to_simulation(client: AsyncClient) -> None:
    response = await client.get("/api/v1/settings/frm")
    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is False
    assert body["source"] == "simulation"
    assert body["connected"] is False


async def test_frm_route_not_shadowed_by_generic_setting(client: AsyncClient) -> None:
    # ``/settings/frm`` must resolve to the typed handler, not ``/settings/{key}``.
    response = await client.get("/api/v1/settings/frm")
    assert response.status_code == 200
    assert "source" in response.json()


async def test_enable_unreachable_frm_falls_back_to_simulation(client: AsyncClient) -> None:
    # An unreachable endpoint is saved but the app stays on simulation (200, not 5xx).
    response = await client.put(
        "/api/v1/settings/frm",
        json={"enabled": True, "base_url": "http://127.0.0.1:9/"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is True
    assert body["base_url"] == "http://127.0.0.1:9"  # trailing slash trimmed
    assert body["source"] == "simulation"
    assert body["connected"] is False
    assert "unreachable" in (body["message"] or "").lower()

    # The dashboard keeps serving simulated data.
    dash = (await client.get("/api/v1/dashboard")).json()
    assert dash["source"] == "simulation"


async def test_disable_frm_reports_simulation(client: AsyncClient) -> None:
    response = await client.put(
        "/api/v1/settings/frm",
        json={"enabled": False, "base_url": "http://localhost:8080"},
    )
    assert response.status_code == 200
    assert response.json()["source"] == "simulation"


async def test_frm_config_rejects_bad_url(client: AsyncClient) -> None:
    response = await client.put(
        "/api/v1/settings/frm",
        json={"enabled": True, "base_url": "localhost:8080"},
    )
    assert response.status_code == 422


async def test_frm_test_probe_unreachable(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/settings/frm/test",
        json={"enabled": True, "base_url": "http://127.0.0.1:9"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["reachable"] is False
    assert body["base_url"] == "http://127.0.0.1:9"
