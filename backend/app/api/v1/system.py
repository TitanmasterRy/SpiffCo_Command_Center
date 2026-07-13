"""System endpoints: health, app info, persisted settings."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, get_settings
from app.config.settings import Settings
from app.connectors.frm import ConnectionState, FrmConnector
from app.schemas.system import (
    AppInfo,
    FrmConfig,
    FrmConfigStatus,
    FrmTestResult,
    HealthStatus,
    SettingValue,
)
from app.services import system_service
from app.services.frm_config import FrmConfigService

router = APIRouter(tags=["system"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def _frm_health(request: Request) -> str:
    """Map the FRM connector state to a health value (or ``not_configured``)."""
    connector: FrmConnector | None = getattr(request.app.state, "frm", None)
    if connector is None:
        return "not_configured"
    return "connected" if connector.state == ConnectionState.CONNECTED else "disconnected"


def _frm_config(request: Request) -> FrmConfigService:
    """Return the runtime FRM-configuration service from app state."""
    service: FrmConfigService = request.app.state.frm_config
    return service


@router.get("/health", response_model=HealthStatus)
async def health(request: Request, session: SessionDep, settings: SettingsDep) -> HealthStatus:
    """Report backend health including database and FRM connectivity."""
    return await system_service.get_health(session, settings, _frm_health(request))


@router.get("/info", response_model=AppInfo)
async def info(settings: SettingsDep) -> AppInfo:
    """Return application name, version, and environment."""
    return system_service.get_app_info(settings)


@router.get("/settings", response_model=list[SettingValue])
async def list_settings(session: SessionDep) -> list[SettingValue]:
    """List all persisted user settings."""
    return await system_service.list_settings(session)


@router.get("/settings/frm", response_model=FrmConfigStatus)
async def get_frm_config(request: Request) -> FrmConfigStatus:
    """Return the current FRM connection config and live connection state."""
    return _frm_config(request).status()


@router.put("/settings/frm", response_model=FrmConfigStatus)
async def update_frm_config(request: Request, body: FrmConfig) -> FrmConfigStatus:
    """Persist and apply an FRM config change (reconnects live, no restart)."""
    return await _frm_config(request).apply(body)


@router.post("/settings/frm/test", response_model=FrmTestResult)
async def test_frm_config(request: Request, body: FrmConfig) -> FrmTestResult:
    """Probe an FRM endpoint for reachability without saving it."""
    return await _frm_config(request).test(body.base_url)


@router.get("/settings/{key}", response_model=SettingValue)
async def get_setting(key: str, session: SessionDep) -> SettingValue:
    """Fetch a single setting by key (404 if absent)."""
    return await system_service.get_setting(session, key)


@router.put("/settings/{key}", response_model=SettingValue)
async def put_setting(key: str, body: SettingValue, session: SessionDep) -> SettingValue:
    """Create or replace a setting. The path key wins over the body key."""
    return await system_service.put_setting(session, SettingValue(key=key, value=body.value))
