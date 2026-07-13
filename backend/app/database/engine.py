"""Async SQLAlchemy engine and session lifecycle.

SQLite (via ``aiosqlite``) is the default; the URL is fully configurable so a
later migration to PostgreSQL (``postgresql+asyncpg://``) needs no code changes.

The engine is created lazily at startup by :func:`init_database` and disposed by
:func:`shutdown_database`. Request handlers obtain sessions through the
:func:`get_session` FastAPI dependency.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config.settings import Settings
from app.models.base import Base

logger = logging.getLogger(__name__)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


async def init_database(settings: Settings) -> None:
    """Create the engine/session factory and ensure the schema exists.

    Uses ``create_all`` for now; Alembic migrations are planned once the schema
    stabilizes (documented in docs/KNOWN_LIMITATIONS.md).
    """
    global _engine, _session_factory
    _engine = create_async_engine(settings.database_url, echo=False, future=True)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database ready at %s", settings.database_url)


async def shutdown_database() -> None:
    """Dispose of the engine and reset module state."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the session factory for use outside request scope (workers)."""
    if _session_factory is None:
        raise RuntimeError("Database not initialized — init_database() must run at startup")
    return _session_factory


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a database session per request."""
    if _session_factory is None:
        raise RuntimeError("Database not initialized — init_database() must run at startup")
    async with _session_factory() as session:
        yield session
