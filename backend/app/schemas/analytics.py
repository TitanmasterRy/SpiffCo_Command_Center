"""Schemas for analytics: series statistics, KPIs, and window comparisons.

Aggregates the persisted ``power_samples`` / ``production_samples`` history into
summary statistics (min/max/avg/latest), an uptime KPI, and a recent-vs-previous
window comparison.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SeriesStats(BaseModel):
    """Summary statistics for one numeric series."""

    count: int
    min: float = 0.0
    max: float = 0.0
    avg: float = 0.0
    latest: float = 0.0


class Comparison(BaseModel):
    """Recent half of a series vs. the older half."""

    current_avg: float
    previous_avg: float
    delta: float
    delta_percent: float | None = Field(
        default=None, description="delta / previous_avg; null if previous is ~0"
    )


class PowerAnalytics(BaseModel):
    """Power KPIs across the sampled window."""

    sample_count: int
    produced: SeriesStats
    consumed: SeriesStats
    capacity: SeriesStats
    battery_avg: float
    uptime_percent: float = Field(description="Fraction of samples with produced >= consumed")
    produced_trend: Comparison


class ProductionAnalytics(BaseModel):
    """Production KPIs for one item across the sampled window."""

    item: str
    name: str
    sample_count: int
    rate: SeriesStats
    trend: Comparison


class AnalyticsSummary(BaseModel):
    """Top-level analytics: power KPIs plus the busiest production lines."""

    generated_at: datetime
    sample_limit: int
    power: PowerAnalytics
    top_production: list[ProductionAnalytics]
