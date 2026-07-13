"""Analytics service: aggregate history tables into KPIs and comparisons."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import compute
from app.errors import NotFoundError
from app.models.history import PowerSample, ProductionSample
from app.production.data import item_name
from app.schemas.analytics import (
    AnalyticsSummary,
    PowerAnalytics,
    ProductionAnalytics,
)


async def _power_samples(session: AsyncSession, limit: int) -> list[PowerSample]:
    rows = (
        await session.execute(
            select(PowerSample).order_by(PowerSample.timestamp.desc()).limit(limit)
        )
    ).scalars().all()
    return list(reversed(rows))


async def power_analytics(session: AsyncSession, limit: int = 240) -> PowerAnalytics:
    """Aggregate the recent power samples into KPIs and a produced-trend."""
    samples = await _power_samples(session, limit)
    produced = [s.produced_mw for s in samples]
    consumed = [s.consumed_mw for s in samples]
    capacity = [s.capacity_mw for s in samples]
    battery = [s.battery_percent for s in samples]
    return PowerAnalytics(
        sample_count=len(samples),
        produced=compute.series_stats(produced),
        consumed=compute.series_stats(consumed),
        capacity=compute.series_stats(capacity),
        battery_avg=round(sum(battery) / len(battery), 4) if battery else 0.0,
        uptime_percent=compute.uptime_fraction(list(zip(produced, consumed, strict=True))),
        produced_trend=compute.compare(produced),
    )


async def _production_for(
    session: AsyncSession, item: str, limit: int
) -> ProductionAnalytics:
    rows = (
        await session.execute(
            select(ProductionSample)
            .where(ProductionSample.item == item)
            .order_by(ProductionSample.timestamp.desc())
            .limit(limit)
        )
    ).scalars().all()
    rates = [r.rate_per_min for r in reversed(rows)]
    return ProductionAnalytics(
        item=item,
        name=item_name(item),
        sample_count=len(rates),
        rate=compute.series_stats(rates),
        trend=compute.compare(rates),
    )


async def production_analytics(
    session: AsyncSession, item: str, limit: int = 240
) -> ProductionAnalytics:
    """Analytics for one item, or 404 if it has no samples."""
    result = await _production_for(session, item, limit)
    if result.sample_count == 0:
        raise NotFoundError(f"no production history for {item!r}")
    return result


async def _tracked_items(session: AsyncSession) -> list[str]:
    rows = (
        await session.execute(select(ProductionSample.item).distinct())
    ).scalars().all()
    return list(rows)


async def summary(session: AsyncSession, limit: int = 240, top: int = 5) -> AnalyticsSummary:
    """Power KPIs plus the busiest production lines (by average rate)."""
    power = await power_analytics(session, limit)
    items = await _tracked_items(session)
    production = [await _production_for(session, item, limit) for item in items]
    production.sort(key=lambda p: p.rate.avg, reverse=True)
    return AnalyticsSummary(
        generated_at=datetime.now(UTC),
        sample_limit=limit,
        power=power,
        top_production=production[:top],
    )
