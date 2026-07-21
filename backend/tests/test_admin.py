"""Tests for the admin panel: auth, catalog, execution, presets."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from app.config.settings import get_settings
from app.services.admin_auth import AdminAuthService, _verify_hash, hash_password


@pytest.fixture
async def admin_client() -> AsyncIterator[AsyncClient]:
    """Client against an app with login enabled and the owner account seeded."""
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
        del os.environ["SPIFFCO_AUTH_ENABLED"]
        del os.environ["SPIFFCO_ADMIN_USERNAME"]
        del os.environ["SPIFFCO_ADMIN_PASSWORD"]
        get_settings.cache_clear()


async def _login(client: AsyncClient) -> dict[str, str]:
    """Log in as the seeded owner account and return an auth header."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "pioneer", "password": "ficsit-do-not-tell"},
    )
    assert response.status_code == 200
    token = response.json()["token"]
    return {"Authorization": f"Bearer {token}"}


class TestAuth:
    async def test_cheats_open_when_auth_disabled(self, client: AsyncClient) -> None:
        # With SPIFFCO_AUTH_ENABLED unset (default), the app runs single-user and
        # every request is a local superuser — cheat endpoints need no token.
        assert (await client.get("/api/v1/admin/catalog")).status_code == 200

    async def test_login_wrong_password(self, admin_client: AsyncClient) -> None:
        response = await admin_client.post(
            "/api/v1/auth/login", json={"username": "pioneer", "password": "wrong"}
        )
        assert response.status_code == 401

    async def test_login_and_session(self, admin_client: AsyncClient) -> None:
        headers = await _login(admin_client)
        response = await admin_client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 200
        body = response.json()
        assert body["username"] == "pioneer"
        assert body["is_superuser"] is True
        assert "use:admin-cheats" in body["permissions"]

    async def test_endpoints_require_auth(self, admin_client: AsyncClient) -> None:
        for path in ("/api/v1/admin/catalog", "/api/v1/admin/state", "/api/v1/admin/log"):
            assert (await admin_client.get(path)).status_code == 401

    async def test_tampered_token_rejected(self, admin_client: AsyncClient) -> None:
        headers = await _login(admin_client)
        forged = headers["Authorization"][:-4] + "0000"
        response = await admin_client.get(
            "/api/v1/admin/catalog", headers={"Authorization": forged}
        )
        assert response.status_code == 401

    def test_password_hash_roundtrip(self) -> None:
        encoded = hash_password("s3cret", iterations=1000)
        assert _verify_hash("s3cret", encoded)
        assert not _verify_hash("wrong", encoded)
        assert not _verify_hash("s3cret", "garbage")


class TestCheats:
    async def test_catalog_shape(self, admin_client: AsyncClient) -> None:
        headers = await _login(admin_client)
        response = await admin_client.get("/api/v1/admin/catalog", headers=headers)
        assert response.status_code == 200
        body = response.json()
        assert body["executor"] == "simulated"
        ids = {c["id"] for c in body["categories"]}
        assert {"player", "building", "power", "logistics", "trains", "drones",
                "world", "creatures", "radiation", "analysis", "inspector",
                "appearance"} <= ids
        # Action ids are unique across the whole catalog.
        all_ids = [a["id"] for c in body["categories"] for s in c["sections"]
                   for a in s["actions"]]
        assert len(all_ids) == len(set(all_ids))

    async def test_scope_and_affects_all_flags(self, admin_client: AsyncClient) -> None:
        headers = await _login(admin_client)
        body = (await admin_client.get("/api/v1/admin/catalog", headers=headers)).json()
        actions = {a["id"]: a for c in body["categories"] for s in c["sections"]
                   for a in s["actions"]}
        # Player-scoped: UI shows an online-player selector.
        assert actions["player.infinite_health"]["scope"] == "player"
        assert actions["player.spawn_item"]["scope"] == "player"
        assert actions["appearance.xray"]["scope"] == "player"
        assert actions["analysis.idle"]["scope"] == "player"
        # Shared-state mutations are flagged for the "all players" badge.
        for action_id in ("player.unlock_all_recipes", "build.delete_factory",
                          "power.infinite", "world.freeze_time", "trains.pause"):
            assert actions[action_id]["scope"] == "world", action_id
            assert actions[action_id]["affects_all"] is True, action_id
        # Per-player visuals and the inspector never carry the badge.
        assert actions["radiation.visualize"]["affects_all"] is False
        assert actions["inspector.inspect"]["affects_all"] is False

    async def test_execute_targets_player_in_log(self, admin_client: AsyncClient) -> None:
        headers = await _login(admin_client)
        response = await admin_client.post(
            "/api/v1/admin/execute",
            json={"action_id": "player.infinite_health", "params": {"player": "Rylen"}},
            headers=headers,
        )
        assert response.status_code == 200
        log = (await admin_client.get("/api/v1/admin/log", headers=headers)).json()
        assert log[0]["params"] == {"player": "Rylen"}

    async def test_execute_button_and_log(self, admin_client: AsyncClient) -> None:
        headers = await _login(admin_client)
        response = await admin_client.post(
            "/api/v1/admin/execute",
            json={"action_id": "player.spawn_item",
                  "params": {"item": "Iron Plate", "quantity": 100}},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "simulated"

        log = (await admin_client.get("/api/v1/admin/log", headers=headers)).json()
        assert log[0]["action_id"] == "player.spawn_item"
        assert log[0]["username"] == "pioneer"

    async def test_toggle_flips_state(self, admin_client: AsyncClient) -> None:
        headers = await _login(admin_client)
        for expected in (True, False):
            response = await admin_client.post(
                "/api/v1/admin/execute",
                json={"action_id": "player.infinite_health", "params": {}},
                headers=headers,
            )
            assert response.json()["toggles"]["player.infinite_health"] is expected

    async def test_unknown_action_404(self, admin_client: AsyncClient) -> None:
        headers = await _login(admin_client)
        response = await admin_client.post(
            "/api/v1/admin/execute", json={"action_id": "nope.nothing"}, headers=headers
        )
        assert response.status_code == 404

    async def test_missing_param_422(self, admin_client: AsyncClient) -> None:
        headers = await _login(admin_client)
        response = await admin_client.post(
            "/api/v1/admin/execute",
            json={"action_id": "player.teleport_waypoint", "params": {}},
            headers=headers,
        )
        assert response.status_code == 422

    async def test_presets_roundtrip(self, admin_client: AsyncClient) -> None:
        headers = await _login(admin_client)
        items = [{"name": "Home base", "coords": "0,0,15000"}]
        put = await admin_client.put(
            "/api/v1/admin/presets/teleports",
            json={"kind": "ignored", "items": items},
            headers=headers,
        )
        assert put.status_code == 200
        got = await admin_client.get("/api/v1/admin/presets/teleports", headers=headers)
        assert got.json() == {"kind": "teleports", "items": items}

    async def test_invalid_preset_kind(self, admin_client: AsyncClient) -> None:
        headers = await _login(admin_client)
        response = await admin_client.get(
            "/api/v1/admin/presets/bad%20kind%21", headers=headers
        )
        assert response.status_code == 422


class TestCommandEndpointExecutor:
    async def test_dispatch_sends_token_and_payload(self) -> None:
        import httpx

        from app.services.admin_cheats import CommandEndpointExecutor

        seen: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["token"] = request.headers.get("X-SpiffCo-Token")
            seen["body"] = request.content
            return httpx.Response(200, json={"ok": True})

        executor = CommandEndpointExecutor(
            "http://bridge:8091", token="s3cret", transport=httpx.MockTransport(handler)
        )
        try:
            result = await executor.execute("player.fly", {}, True)
        finally:
            await executor.aclose()
        assert result == {"ok": True}
        assert seen["token"] == "s3cret"
        assert seen["body"] == b'{"action":"player.fly","params":{},"enabled":true}'

    async def test_unsupported_action_raises_upstream_error(self) -> None:
        import httpx

        from app.errors import UpstreamUnavailableError
        from app.services.admin_cheats import CommandEndpointExecutor

        executor = CommandEndpointExecutor(
            "http://bridge:8091",
            transport=httpx.MockTransport(lambda _: httpx.Response(501)),
        )
        try:
            with pytest.raises(UpstreamUnavailableError):
                await executor.execute("nope", {}, None)
        finally:
            await executor.aclose()


class TestAuthService:
    def test_hash_wins_over_plaintext(self) -> None:
        settings = get_settings().model_copy(update={
            "admin_username": "admin",
            "admin_password": "plain",
            "admin_password_hash": hash_password("hashed", iterations=1000),
        })
        service = AdminAuthService(settings)
        assert service.login("admin", "hashed").username == "admin"
        from app.errors import UnauthorizedError

        with pytest.raises(UnauthorizedError):
            service.login("admin", "plain")


class TestItemCatalog:
    async def test_requires_auth(self, admin_client: AsyncClient) -> None:
        assert (await admin_client.get("/api/v1/admin/item-catalog")).status_code == 401

    async def test_returns_full_catalogue(self, admin_client: AsyncClient) -> None:
        headers = await _login(admin_client)
        response = await admin_client.get("/api/v1/admin/item-catalog", headers=headers)
        assert response.status_code == 200
        items = response.json()
        # The whole game has ~195 giveable items; guard against a truncated seed.
        assert len(items) > 150
        by_name = {i["name"]: i for i in items}
        assert by_name["Iron Plate"]["class_name"] == "Desc_IronPlate_C"
        assert by_name["Iron Plate"]["category"] == "Part"
        assert {i["category"] for i in items} >= {"Part", "Resource", "Equipment", "Ammunition"}
        # Every entry carries a spawnable game class name.
        assert all(i["class_name"].endswith("_C") for i in items)
