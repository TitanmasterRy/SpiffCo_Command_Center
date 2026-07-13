"""System service: health checks, app info, persisted settings."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app import __version__
from app.config.settings import Settings
from app.errors import NotFoundError
from app.models.app_setting import AppSetting
from app.schemas.system import AppInfo, HealthStatus, SettingValue

_STARTED_AT = time.monotonic()


def get_app_info(settings: Settings) -> AppInfo:
    """Return static application metadata."""
    return AppInfo(
        name=settings.app_name,
        version=__version__,
        environment=settings.environment.value,
    )


async def get_health(session: AsyncSession, settings: Settings) -> HealthStatus:
    """Probe dependencies and report overall health.

    The FRM state is ``not_configured`` until the Phase 11 connector lands.
    """
    try:
        await session.execute(text("SELECT 1"))
        database = "ok"
    except Exception:
        database = "error"

    return HealthStatus(
        status="ok" if database == "ok" else "degraded",
        version=__version__,
        environment=settings.environment.value,
        database=database,  # type: ignore[arg-type]
        frm="not_configured",
        uptime_seconds=time.monotonic() - _STARTED_AT,
        server_time=datetime.now(timezone.utc),
    )


async def list_settings(session: AsyncSession) -> list[SettingValue]:
    """Return all persisted user settings."""
    rows = (await session.execute(select(AppSetting))).scalars().all()
    return [SettingValue(key=row.key, value=json.loads(row.value)) for row in rows]


async def get_setting(session: AsyncSession, key: str) -> SettingValue:
    """Return one setting or raise :class:`NotFoundError`."""
    row = await session.get(AppSetting, key)
    if row is None:
        raise NotFoundError(f"setting {key!r} does not exist")
    return SettingValue(key=row.key, value=json.loads(row.value))


async def put_setting(session: AsyncSession, setting: SettingValue) -> SettingValue:
    """Create or update a setting (value stored as JSON)."""
    row = await session.get(AppSetting, setting.key)
    encoded = json.dumps(setting.value)
    if row is None:
        session.add(AppSetting(key=setting.key, value=encoded))
    else:
        row.value = encoded
    await session.commit()
    return setting
