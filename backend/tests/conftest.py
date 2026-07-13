"""Shared test fixtures.

Tests run against an in-memory SQLite database and a real app instance whose
lifespan (database, event bus, scheduler) is driven by the ASGI transport.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

os.environ["SPIFFCO_DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["SPIFFCO_ENVIRONMENT"] = "test"
os.environ["SPIFFCO_LOG_LEVEL"] = "WARNING"
# Keep the periodic scheduler off so background DB writes never race the request
# handlers on the shared in-memory connection (deterministic, warning-free tests).
os.environ["SPIFFCO_SCHEDULER_ENABLED"] = "false"

from app.config.settings import get_settings  # noqa: E402

get_settings.cache_clear()

from app.main import create_app  # noqa: E402


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """HTTP client against a freshly started app (lifespan included).

    httpx's ASGITransport does not run startup/shutdown events, so
    LifespanManager drives them explicitly.
    """
    app = create_app()
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as http:
            yield http
