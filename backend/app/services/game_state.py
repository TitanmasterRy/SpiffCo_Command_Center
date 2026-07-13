"""Game-state service: holds the latest snapshot and records history.

The provider is pluggable: ``SimulatedGameProvider`` today, the FRM connector
in Phase 11 — consumers only ever see normalized schemas.
"""

from __future__ import annotations

from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.errors import UpstreamUnavailableError
from app.models.history import PowerSample, ProductionSample
from app.schemas.dashboard import (
    DashboardSnapshot,
    PowerHistoryPoint,
    ProductionHistoryPoint,
)
from app.services.event_bus import EventBus


class GameStateProvider(Protocol):
    """Anything that can produce a normalized dashboard snapshot."""

    def snapshot(self) -> DashboardSnapshot: ...


class GameStateService:
    """Refreshes state from the provider, publishes it, and samples history."""

    def __init__(self, provider: GameStateProvider, bus: EventBus) -> None:
        self._provider = provider
        self._bus = bus
        self._latest: DashboardSnapshot | None = None

    @property
    def latest(self) -> DashboardSnapshot:
        """Most recent snapshot; 503 until the first refresh has run."""
        if self._latest is None:
            raise UpstreamUnavailableError("No game state available yet")
        return self._latest

    async def refresh(self) -> DashboardSnapshot:
        """Pull a fresh snapshot and publish it on ``dashboard.snapshot``."""
        self._latest = self._provider.snapshot()
        self._bus.publish("dashboard.snapshot", self._latest.model_dump(mode="json"))
        return self._latest

    async def record_history(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Persist one power sample and one production sample per item."""
        if self._latest is None:
            return
        snap = self._latest
        async with session_factory() as session:
            session.add(
                PowerSample(
                    timestamp=snap.generated_at,
                    produced_mw=snap.power.produced_mw,
                    consumed_mw=snap.power.consumed_mw,
                    capacity_mw=snap.power.capacity_mw,
                    battery_percent=snap.power.battery_percent,
                )
            )
            session.add_all(
                ProductionSample(
                    timestamp=snap.generated_at, item=p.item, rate_per_min=p.current_per_min
                )
                for p in snap.production
            )
            await session.commit()


async def get_power_history(session: AsyncSession, limit: int = 120) -> list[PowerHistoryPoint]:
    """Latest *limit* power samples, oldest first."""
    rows = (
        await session.execute(
            select(PowerSample).order_by(PowerSample.timestamp.desc()).limit(limit)
        )
    ).scalars().all()
    return [
        PowerHistoryPoint(
            timestamp=r.timestamp,
            produced_mw=r.produced_mw,
            consumed_mw=r.consumed_mw,
            capacity_mw=r.capacity_mw,
            battery_percent=r.battery_percent,
        )
        for r in reversed(rows)
    ]


async def get_production_history(
    session: AsyncSession, item: str, limit: int = 120
) -> list[ProductionHistoryPoint]:
    """Latest *limit* production samples for *item*, oldest first."""
    rows = (
        await session.execute(
            select(ProductionSample)
            .where(ProductionSample.item == item)
            .order_by(ProductionSample.timestamp.desc())
            .limit(limit)
        )
    ).scalars().all()
    return [
        ProductionHistoryPoint(timestamp=r.timestamp, item=r.item, rate_per_min=r.rate_per_min)
        for r in reversed(rows)
    ]
