"""Tests for the system endpoints (health, info, settings) and error envelope."""

from __future__ import annotations

from httpx import AsyncClient


async def test_health_reports_ok(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["environment"] == "test"
    assert body["uptime_seconds"] >= 0


async def test_info_returns_metadata(client: AsyncClient) -> None:
    response = await client.get("/api/v1/info")
    assert response.status_code == 200
    body = response.json()
    assert body["name"]
    assert body["version"]


async def test_settings_roundtrip(client: AsyncClient) -> None:
    put = await client.put(
        "/api/v1/settings/ui.theme", json={"key": "ignored", "value": {"mode": "dark"}}
    )
    assert put.status_code == 200
    assert put.json() == {"key": "ui.theme", "value": {"mode": "dark"}}

    get = await client.get("/api/v1/settings/ui.theme")
    assert get.status_code == 200
    assert get.json()["value"] == {"mode": "dark"}

    listing = await client.get("/api/v1/settings")
    assert listing.status_code == 200
    assert any(item["key"] == "ui.theme" for item in listing.json())


async def test_missing_setting_uses_error_envelope(client: AsyncClient) -> None:
    response = await client.get("/api/v1/settings/does.not.exist")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "not_found"
    assert "does.not.exist" in body["error"]["message"]
