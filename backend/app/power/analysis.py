"""Pure power-grid analysis: headroom, battery projection, recommendations.

No I/O — takes a normalized :class:`~app.schemas.dashboard.PowerStats` and returns
analysis values, so it is trivially unit-testable and reused by the service.
"""

from __future__ import annotations

from app.schemas.dashboard import PowerStats
from app.schemas.power import BatteryStatus, PowerRecommendation, PowerStatus

# Below this fraction of spare capacity the grid is one machine away from tripping.
_LOW_HEADROOM = 0.1
# A battery this low, and draining, is worth warning about.
_LOW_BATTERY = 0.2
# Net MW under this magnitude counts as a stable (neither charging nor draining).
_STABLE_EPS = 0.05


def headroom(power: PowerStats) -> tuple[float, float, PowerStatus]:
    """Return (headroom_mw, headroom_fraction, status) for the grid."""
    spare = power.capacity_mw - power.consumed_mw
    fraction = spare / power.capacity_mw if power.capacity_mw > 0 else 0.0
    if power.fuse_triggered or spare < 0:
        status: PowerStatus = "critical"
    elif fraction < _LOW_HEADROOM:
        status = "warn"
    else:
        status = "ok"
    return round(spare, 3), round(fraction, 4), status


def battery(power: PowerStats) -> BatteryStatus:
    """Project battery trend and minutes to empty/full from the current net draw."""
    stored = power.battery_percent * power.battery_capacity_mwh
    net = power.produced_mw - power.consumed_mw  # +ve charges the battery
    minutes: float | None = None
    if net > _STABLE_EPS:
        trend = "charging"
        free = power.battery_capacity_mwh - stored
        minutes = round(free / net * 60, 1) if free > 0 else 0.0
    elif net < -_STABLE_EPS:
        trend = "draining"
        minutes = round(stored / (-net) * 60, 1) if stored > 0 else 0.0
    else:
        trend = "stable"
    return BatteryStatus(
        percent=power.battery_percent,
        capacity_mwh=power.battery_capacity_mwh,
        stored_mwh=round(stored, 3),
        trend=trend,
        minutes_remaining=minutes,
    )


def recommend(
    power: PowerStats, headroom_fraction: float, status: PowerStatus, batt: BatteryStatus
) -> list[PowerRecommendation]:
    """Rule-based recommendations (precursor to the Phase 10 advisor)."""
    tips: list[PowerRecommendation] = []
    if status == "critical":
        tips.append(
            PowerRecommendation(
                severity="critical",
                title="Demand exceeds capacity",
                message=(
                    f"Consumption ({power.consumed_mw:.0f} MW) is at or above capacity "
                    f"({power.capacity_mw:.0f} MW). Add generation or shed load before a fuse trip."
                ),
            )
        )
    elif headroom_fraction < _LOW_HEADROOM:
        tips.append(
            PowerRecommendation(
                severity="warning",
                title="Low power headroom",
                message=(
                    f"Only {headroom_fraction * 100:.0f}% spare capacity remaining. "
                    "Bring more generators online before expanding."
                ),
            )
        )

    if batt.trend == "draining" and batt.minutes_remaining is not None:
        severity = "critical" if batt.minutes_remaining < 5 else "warning"
        tips.append(
            PowerRecommendation(
                severity=severity,
                title="Battery draining",
                message=(
                    f"Batteries are discharging (~{batt.minutes_remaining:.0f} min to empty). "
                    "Generation is below consumption."
                ),
            )
        )
    elif batt.percent < _LOW_BATTERY and batt.trend != "charging":
        tips.append(
            PowerRecommendation(
                severity="warning",
                title="Battery reserve low",
                message=f"Battery at {batt.percent * 100:.0f}%; little buffer for demand spikes.",
            )
        )

    if not tips:
        tips.append(
            PowerRecommendation(
                severity="info",
                title="Grid healthy",
                message="Generation comfortably covers demand with headroom to spare.",
            )
        )
    return tips
