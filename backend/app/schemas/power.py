"""Schemas for the power page: generator catalog, grid analysis, battery, tips.

Builds on the dashboard's live :class:`~app.schemas.dashboard.PowerStats` and
persisted ``power_samples``, adding a headroom/battery analysis and rule-based
recommendations (a Phase 10 advisor precursor).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.dashboard import PowerHistoryPoint, PowerStats, Severity

PowerStatus = Literal["ok", "warn", "critical"]
BatteryTrend = Literal["charging", "draining", "stable"]


class PowerBuildingInfo(BaseModel):
    """A generator (or power storage) from the static catalog."""

    id: str
    name: str
    power_mw: float = Field(description="Output MW (0 for storage)")
    fuel: str | None = None
    fuel_rate: float | None = None
    requires_water: bool = False
    water_rate: float | None = None
    capacity_mwh: float | None = None
    max_charge_mw: float | None = None


class BatteryStatus(BaseModel):
    """Battery state and its projected time to empty/full."""

    percent: float = Field(ge=0, le=1)
    capacity_mwh: float
    stored_mwh: float
    trend: BatteryTrend
    minutes_remaining: float | None = Field(
        default=None, description="Minutes to empty (draining) or full (charging); null if stable"
    )


class PowerRecommendation(BaseModel):
    """A single actionable recommendation about the power grid."""

    severity: Severity
    title: str
    message: str


class PowerReport(BaseModel):
    """Complete power page payload: live stats, analysis, history, tips."""

    generated_at: datetime
    source: Literal["simulation", "frm"]
    power: PowerStats
    headroom_mw: float = Field(description="capacity - consumed (negative = over capacity)")
    headroom_percent: float = Field(description="headroom / capacity (0..1; negative if over)")
    status: PowerStatus
    battery: BatteryStatus
    recommendations: list[PowerRecommendation]
    history: list[PowerHistoryPoint]
