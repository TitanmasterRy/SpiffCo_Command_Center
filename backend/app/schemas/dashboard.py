"""Schemas for the dashboard: live snapshot and history samples."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Severity = Literal["info", "warning", "critical"]
FactoryState = Literal["ok", "warn", "error", "idle"]


class MachineSummary(BaseModel):
    """Machine counts by state."""

    total: int = 0
    running: int = 0
    idle: int = 0
    unpowered: int = 0


class FactoryStatus(BaseModel):
    """Status of one logical factory."""

    id: str
    name: str
    status: FactoryState
    efficiency: float = Field(ge=0, le=1, description="0..1 fraction of target output")
    machines: MachineSummary


class PowerStats(BaseModel):
    """Grid-wide power state (MW / MWh / 0..1 fractions)."""

    produced_mw: float
    consumed_mw: float
    capacity_mw: float
    battery_percent: float = Field(ge=0, le=1)
    battery_capacity_mwh: float
    fuse_triggered: bool = False


class ProductionStat(BaseModel):
    """Current vs. target output for one item (per minute)."""

    item: str
    name: str
    current_per_min: float
    target_per_min: float


class StorageLevel(BaseModel):
    """Fill level of tracked storage for one item."""

    item: str
    name: str
    stored: float
    capacity: float


class Alert(BaseModel):
    """An active alert derived from game state."""

    id: str
    severity: Severity
    title: str
    message: str
    source: str


class DashboardSnapshot(BaseModel):
    """Complete dashboard state pushed on topic ``dashboard.snapshot``."""

    generated_at: datetime
    source: Literal["simulation", "frm", "save"]
    power: PowerStats
    machines: MachineSummary
    factories: list[FactoryStatus]
    production: list[ProductionStat]
    storage: list[StorageLevel]
    alerts: list[Alert]


class PowerHistoryPoint(BaseModel):
    """One persisted power sample."""

    timestamp: datetime
    produced_mw: float
    consumed_mw: float
    capacity_mw: float
    battery_percent: float


class ProductionHistoryPoint(BaseModel):
    """One persisted production-rate sample."""

    timestamp: datetime
    item: str
    rate_per_min: float
