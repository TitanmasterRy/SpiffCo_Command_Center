"""System endpoints: health, app info, persisted settings."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, get_settings
from app.config.settings import Settings
from app.schemas.system import AppInfo, HealthStatus, SettingValue
from app.services import system_service

router = APIRouter(tags=["system"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


@router.get("/health", response_model=HealthStatus)
async def health(session: SessionDep, settings: SettingsDep) -> HealthStatus:
    """Report backend health including database and FRM connectivity."""
    return await system_service.get_health(session, settings)


@router.get("/info", response_model=AppInfo)
async def info(settings: SettingsDep) -> AppInfo:
    """Return application name, version, and environment."""
    return system_service.get_app_info(settings)


@router.get("/settings", response_model=list[SettingValue])
async def list_settings(session: SessionDep) -> list[SettingValue]:
    """List all persisted user settings."""
    return await system_service.list_settings(session)


@router.get("/settings/{key}", response_model=SettingValue)
async def get_setting(key: str, session: SessionDep) -> SettingValue:
    """Fetch a single setting by key (404 if absent)."""
    return await system_service.get_setting(session, key)


@router.put("/settings/{key}", response_model=SettingValue)
async def put_setting(key: str, body: SettingValue, session: SessionDep) -> SettingValue:
    """Create or replace a setting. The path key wins over the body key."""
    return await system_service.put_setting(session, SettingValue(key=key, value=body.value))
