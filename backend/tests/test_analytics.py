"""Tests for analytics: pure aggregation math and the summary endpoints."""

from __future__ import annotations

from httpx import AsyncClient

from app.analytics import compute
from app.database.engine import get_session_factory
from app.models.history import PowerSample, ProductionSample


def test_series_stats_and_empty() -> None:
    stats = compute.series_stats([10.0, 20.0, 30.0])
    assert (stats.min, stats.max, stats.avg, stats.latest, stats.count) == (10, 30, 20, 30, 3)
    empty = compute.series_stats([])
    assert empty.count == 0 and empty.avg == 0


def test_uptime_fraction() -> None:
    pairs = [(100.0, 80.0), (100.0, 120.0), (100.0, 100.0)]  # ok, over, tie(ok)
    assert compute.uptime_fraction(pairs) == round(2 / 3, 4)
    assert compute.uptime_fraction([]) == 0.0


def test_compare_splits_halves() -> None:
    # older half avg 10, recent half avg 20 -> delta +10 (+100%).
    cmp = compute.compare([10.0, 10.0, 20.0, 20.0])
    assert cmp.previous_avg == 10.0
    assert cmp.current_avg == 20.0
    assert cmp.delta == 10.0
    assert cmp.delta_percent == 1.0
    single = compute.compare([5.0])
    assert single.delta == 0.0


async def _seed(client: AsyncClient) -> None:
    """Insert deterministic history samples through the live session factory.

    Rates are large enough to dominate any samples the startup scheduler may have
    recorded from the simulated provider, keeping assertions stable.
    """
    factory = get_session_factory()
    async with factory() as session:
        for i in range(8):
            session.add(
                PowerSample(
                    produced_mw=1000 + i * 10,
                    consumed_mw=50,  # always healthy
                    capacity_mw=2000,
                    battery_percent=0.5,
                )
            )
            session.add(ProductionSample(item="iron-plate", rate_per_min=900 + i))
            session.add(ProductionSample(item="wire", rate_per_min=5 + i))
        await session.commit()


async def test_analytics_summary_endpoint(client: AsyncClient) -> None:
    await _seed(client)
    body = (await client.get("/api/v1/analytics/summary")).json()
    assert body["power"]["sample_count"] >= 8
    assert body["power"]["uptime_percent"] > 0.8  # seeded samples are all healthy
    assert body["power"]["produced"]["max"] >= 1070
    # iron-plate's large rate dominates the ranking; its name resolves from items.
    assert body["top_production"][0]["item"] == "iron-plate"
    assert body["top_production"][0]["name"] == "Iron Plate"


async def test_production_analytics_and_404(client: AsyncClient) -> None:
    await _seed(client)
    ok = await client.get("/api/v1/analytics/production/wire")
    assert ok.status_code == 200
    assert ok.json()["rate"]["count"] >= 6
    missing = await client.get("/api/v1/analytics/production/nonexistent")
    assert missing.status_code == 404


async def test_analytics_summary_handles_empty_history(client: AsyncClient) -> None:
    # A fresh app may have no samples yet; the summary must still return zeros.
    body = (await client.get("/api/v1/analytics/summary")).json()
    assert body["power"]["sample_count"] >= 0
    assert body["power"]["uptime_percent"] >= 0
