"""Schemas for system-level endpoints (health, app info, settings)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


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


class WsEnvelope(BaseModel):
    """Envelope for every message pushed over the WebSocket."""

    topic: str
    timestamp: datetime
    payload: object
