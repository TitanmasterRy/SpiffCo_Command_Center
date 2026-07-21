"""Tests for user auth: registration, approval, and per-user permissions."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from app.config.settings import get_settings


@pytest.fixture
async def auth_client() -> AsyncIterator[AsyncClient]:
    """App with login enabled and the owner account (pioneer) seeded."""
    os.environ["SPIFFCO_AUTH_ENABLED"] = "true"
    os.environ["SPIFFCO_ADMIN_USERNAME"] = "pioneer"
    os.environ["SPIFFCO_ADMIN_PASSWORD"] = "ficsit-do-not-tell"
    get_settings.cache_clear()
    from app.main import create_app

    app = create_app()
    try:
        async with LifespanManager(app):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as http:
                yield http
    finally:
        for key in ("SPIFFCO_AUTH_ENABLED", "SPIFFCO_ADMIN_USERNAME", "SPIFFCO_ADMIN_PASSWORD"):
            os.environ.pop(key, None)
        get_settings.cache_clear()


async def _owner(client: AsyncClient) -> dict[str, str]:
    resp = await client.post(
        "/api/v1/auth/login", json={"username": "pioneer", "password": "ficsit-do-not-tell"}
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['token']}"}


async def _register(client: AsyncClient, username: str = "newbie") -> None:
    resp = await client.post(
        "/api/v1/auth/register", json={"username": username, "password": "hunter2pass"}
    )
    assert resp.status_code == 201, resp.text


class TestConfig:
    async def test_config_reports_enabled(self, auth_client: AsyncClient) -> None:
        body = (await auth_client.get("/api/v1/auth/config")).json()
        assert body == {"enabled": True, "allow_registration": True}

    async def test_config_public_when_disabled(self, client: AsyncClient) -> None:
        body = (await client.get("/api/v1/auth/config")).json()
        assert body["enabled"] is False


class TestRegistration:
    async def test_register_creates_pending_and_blocks_login(
        self, auth_client: AsyncClient
    ) -> None:
        await _register(auth_client)
        login = await auth_client.post(
            "/api/v1/auth/login", json={"username": "newbie", "password": "hunter2pass"}
        )
        assert login.status_code == 401
        assert "awaiting approval" in login.json()["error"]["message"]

    async def test_duplicate_username_conflicts(self, auth_client: AsyncClient) -> None:
        await _register(auth_client)
        resp = await auth_client.post(
            "/api/v1/auth/register", json={"username": "newbie", "password": "hunter2pass"}
        )
        assert resp.status_code == 409

    async def test_short_password_rejected(self, auth_client: AsyncClient) -> None:
        resp = await auth_client.post(
            "/api/v1/auth/register", json={"username": "shorty", "password": "x"}
        )
        assert resp.status_code == 422


class TestApprovalAndPermissions:
    async def test_full_lifecycle(self, auth_client: AsyncClient) -> None:
        owner = await _owner(auth_client)
        await _register(auth_client, "operator1")

        # Owner sees the pending account.
        users = (await auth_client.get("/api/v1/admin/users", headers=owner)).json()
        pending = next(u for u in users if u["username"] == "operator1")
        assert pending["status"] == "pending"

        # Approve as a viewer (no cheat permission).
        approved = await auth_client.post(
            f"/api/v1/admin/users/{pending['id']}/approve",
            json={"role": "viewer"},
            headers=owner,
        )
        assert approved.status_code == 200
        assert approved.json()["status"] == "active"

        # The new user can log in and read a data page...
        login = await auth_client.post(
            "/api/v1/auth/login", json={"username": "operator1", "password": "hunter2pass"}
        )
        assert login.status_code == 200
        member = {"Authorization": f"Bearer {login.json()['token']}"}
        assert (await auth_client.get("/api/v1/dashboard/summary", headers=member)).status_code in (
            200,
            404,
        )
        # ...but is forbidden from the cheat panel.
        assert (await auth_client.get("/api/v1/admin/catalog", headers=member)).status_code == 403
        # ...and cannot manage users.
        assert (await auth_client.get("/api/v1/admin/users", headers=member)).status_code == 403

        # Grant the cheat permission; now the panel opens.
        patched = await auth_client.patch(
            f"/api/v1/admin/users/{pending['id']}",
            json={"permissions": ["view:dashboard", "use:admin-cheats"]},
            headers=owner,
        )
        assert patched.status_code == 200
        login2 = await auth_client.post(
            "/api/v1/auth/login", json={"username": "operator1", "password": "hunter2pass"}
        )
        member2 = {"Authorization": f"Bearer {login2.json()['token']}"}
        assert (await auth_client.get("/api/v1/admin/catalog", headers=member2)).status_code == 200

    async def test_disable_blocks_login(self, auth_client: AsyncClient) -> None:
        owner = await _owner(auth_client)
        await _register(auth_client, "temp")
        users = (await auth_client.get("/api/v1/admin/users", headers=owner)).json()
        uid = next(u["id"] for u in users if u["username"] == "temp")
        await auth_client.post(f"/api/v1/admin/users/{uid}/approve",
                               json={"role": "viewer"}, headers=owner)
        await auth_client.patch(f"/api/v1/admin/users/{uid}",
                                json={"status": "disabled"}, headers=owner)
        login = await auth_client.post(
            "/api/v1/auth/login", json={"username": "temp", "password": "hunter2pass"}
        )
        assert login.status_code == 401

    async def test_owner_cannot_be_deleted(self, auth_client: AsyncClient) -> None:
        owner = await _owner(auth_client)
        users = (await auth_client.get("/api/v1/admin/users", headers=owner)).json()
        owner_id = next(u["id"] for u in users if u["username"] == "pioneer")
        resp = await auth_client.delete(f"/api/v1/admin/users/{owner_id}", headers=owner)
        assert resp.status_code == 409

    async def test_reject_deletes_account(self, auth_client: AsyncClient) -> None:
        owner = await _owner(auth_client)
        await _register(auth_client, "spammer")
        users = (await auth_client.get("/api/v1/admin/users", headers=owner)).json()
        uid = next(u["id"] for u in users if u["username"] == "spammer")
        assert (await auth_client.delete(
            f"/api/v1/admin/users/{uid}", headers=owner)).status_code == 204
        users_after = (await auth_client.get("/api/v1/admin/users", headers=owner)).json()
        assert all(u["username"] != "spammer" for u in users_after)


class TestCatalog:
    async def test_permission_catalog(self, auth_client: AsyncClient) -> None:
        owner = await _owner(auth_client)
        body = (await auth_client.get("/api/v1/auth/catalog", headers=owner)).json()
        keys = {p["key"] for p in body["permissions"]}
        assert "use:admin-cheats" in keys
        assert "manage:users" in keys
        assert "view:dashboard" in keys
        assert set(body["roles"]) == {"viewer", "operator", "admin"}
