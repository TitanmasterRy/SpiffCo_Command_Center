"""Persisted telemetry samples powering history charts."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, utcnow


class PowerSample(Base):
    """Grid power state at one point in time."""

    __tablename__ = "power_samples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    produced_mw: Mapped[float] = mapped_column(Float)
    consumed_mw: Mapped[float] = mapped_column(Float)
    capacity_mw: Mapped[float] = mapped_column(Float)
    battery_percent: Mapped[float] = mapped_column(Float)


class ProductionSample(Base):
    """Output rate of one item at one point in time."""

    __tablename__ = "production_samples"
    __table_args__ = (Index("ix_production_samples_item_ts", "item", "timestamp"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    item: Mapped[str] = mapped_column(String(64))
    rate_per_min: Mapped[float] = mapped_column(Float)
