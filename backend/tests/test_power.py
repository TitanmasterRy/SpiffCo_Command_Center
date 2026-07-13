"""Tests for the power page: headroom/battery analysis, recommendations, API."""

from __future__ import annotations

from httpx import AsyncClient

from app.power import analysis
from app.schemas.dashboard import PowerStats


def _power(**kwargs: float) -> PowerStats:
    base = dict(
        produced_mw=100.0,
        consumed_mw=80.0,
        capacity_mw=150.0,
        battery_percent=0.5,
        battery_capacity_mwh=100.0,
        fuse_triggered=False,
    )
    base.update(kwargs)
    return PowerStats(**base)  # type: ignore[arg-type]


def test_headroom_ok_warn_critical() -> None:
    _, frac, status = analysis.headroom(_power(consumed_mw=80, capacity_mw=150))
    assert status == "ok" and frac > 0.4
    _, _, warn = analysis.headroom(_power(consumed_mw=140, capacity_mw=150))
    assert warn == "warn"
    _, spare_frac, crit = analysis.headroom(_power(consumed_mw=160, capacity_mw=150))
    assert crit == "critical" and spare_frac < 0
    assert analysis.headroom(_power(fuse_triggered=True))[2] == "critical"


def test_battery_charging_draining_stable() -> None:
    charging = analysis.battery(_power(produced_mw=120, consumed_mw=80))
    assert charging.trend == "charging" and charging.minutes_remaining is not None
    draining = analysis.battery(_power(produced_mw=60, consumed_mw=100, battery_percent=0.5))
    assert draining.trend == "draining"
    # 50 MWh stored / 40 MW drain * 60 = 75 min.
    assert draining.minutes_remaining == 75.0
    stable = analysis.battery(_power(produced_mw=100, consumed_mw=100))
    assert stable.trend == "stable" and stable.minutes_remaining is None


def test_recommendations_cover_key_states() -> None:
    power = _power(consumed_mw=160, capacity_mw=150, produced_mw=140)
    spare, frac, status = analysis.headroom(power)
    batt = analysis.battery(power)
    tips = analysis.recommend(power, frac, status, batt)
    assert any(t.severity == "critical" for t in tips)

    healthy = _power(consumed_mw=60, produced_mw=90, capacity_mw=200, battery_percent=0.8)
    s2, f2, st2 = analysis.headroom(healthy)
    b2 = analysis.battery(healthy)
    tips2 = analysis.recommend(healthy, f2, st2, b2)
    assert len(tips2) == 1 and tips2[0].severity == "info"


async def test_power_report_endpoint(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/power")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in {"ok", "warn", "critical"}
    assert "headroom_mw" in body
    assert body["battery"]["trend"] in {"charging", "draining", "stable"}
    assert isinstance(body["recommendations"], list) and body["recommendations"]
    assert isinstance(body["history"], list)


async def test_gamedata_power_endpoint(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/gamedata/power")
    assert resp.status_code == 200
    ids = {b["id"] for b in resp.json()}
    assert {"coal-generator", "nuclear-power-plant"} <= ids
