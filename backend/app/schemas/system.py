"""Schemas for system-level endpoints (health, app info, settings)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class HealthStatus(BaseModel):
    """Liveness/readiness report for the backend and its dependencies."""

    status: Literal["ok", "degraded"] = "ok"
    version: str
    environment: str
    database: Literal["ok", "error"]
    frm: Literal["connected", "disconnected", "not_configured"] = "not_configured"
    uptime_seconds: float = Field(ge=0)
    server_time: datetime


class AppInfo(BaseModel):
    """Static application metadata shown in the UI footer / about dialog."""

    name: str
    version: str
    environment: str


class SettingValue(BaseModel):
    """A persisted key/value user setting (value is arbitrary JSON)."""

    key: str = Field(min_length=1, max_length=128)
    value: object


class FrmConfig(BaseModel):
    """User-editable FRM connection settings (persisted, applied at runtime)."""

    enabled: bool = False
    base_url: str = Field(min_length=1, max_length=2048)

    @field_validator("base_url")
    @classmethod
    def _require_http_scheme(cls, value: str) -> str:
        """Trim and require an ``http(s)://`` URL so the client can reach FRM."""
        trimmed = value.strip().rstrip("/")
        if not trimmed.startswith(("http://", "https://")):
            raise ValueError("base_url must start with http:// or https://")
        return trimmed


class FrmConfigStatus(FrmConfig):
    """Effective FRM configuration plus the live connection state."""

    source: Literal["simulation", "frm", "save"]
    state: Literal["disconnected", "connecting", "connected", "error"]
    connected: bool
    message: str | None = None


class FrmTestResult(BaseModel):
    """Result of probing an FRM endpoint without persisting it."""

    reachable: bool
    base_url: str
    message: str


class WsEnvelope(BaseModel):
    """Envelope for every message pushed over the WebSocket."""

    topic: str
    timestamp: datetime
    payload: object
