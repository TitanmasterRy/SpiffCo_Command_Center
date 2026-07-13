"""Tests for single-origin SPA serving (used by the combined Fly.io deploy)."""

from __future__ import annotations

from pathlib import Path

from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from app.config.settings import Settings
from app.main import create_app


async def _client(static_dir: Path) -> tuple[LifespanManager, AsyncClient]:
    app = create_app(Settings(static_dir=str(static_dir)))
    manager = LifespanManager(app)
    await manager.__aenter__()
    transport = ASGITransport(app=app)
    return manager, AsyncClient(transport=transport, base_url="http://test")


async def test_serves_spa_assets_and_api(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<!doctype html><title>SpiffCo</title>")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("console.log('spiffco')")

    manager, client = await _client(tmp_path)
    try:
        # Deep client-side route falls back to the SPA entrypoint.
        deep = await client.get("/offline")
        assert deep.status_code == 200
        assert "SpiffCo" in deep.text

        # Hashed build assets are served directly.
        asset = await client.get("/assets/app.js")
        assert asset.status_code == 200
        assert "console.log" in asset.text

        # The API still works and unknown API paths stay JSON 404s (not the SPA).
        assert (await client.get("/api/v1/info")).status_code == 200
        missing = await client.get("/api/v1/nope")
        assert missing.status_code == 404
        assert missing.json()["error"]["code"] == "not_found"
    finally:
        await client.aclose()
        await manager.__aexit__(None, None, None)


async def test_no_static_dir_is_noop(tmp_path: Path) -> None:
    # An empty/absent build directory must not register the SPA fallback.
    manager, client = await _client(tmp_path)  # tmp_path has no index.html
    try:
        # With no SPA fallback, an unknown path is a plain 404, not index.html.
        resp = await client.get("/offline")
        assert resp.status_code == 404
    finally:
        await client.aclose()
        await manager.__aexit__(None, None, None)
