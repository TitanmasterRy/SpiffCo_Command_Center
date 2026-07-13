"""Power service: assemble the power report from live stats + history."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.power import analysis
from app.schemas.dashboard import PowerStats
from app.schemas.power import PowerReport
from app.services.game_state import get_power_history


async def build_report(
    session: AsyncSession, power: PowerStats, source: str, history_limit: int = 120
) -> PowerReport:
    """Combine current grid stats, derived analysis, and recent history.

    Args:
        session: DB session for reading persisted power samples.
        power: Latest live grid stats (from the game-state snapshot).
        source: ``"simulation"`` or ``"frm"`` — carried through for the UI badge.
        history_limit: How many recent power samples to include for the chart.
    """
    spare, fraction, status = analysis.headroom(power)
    batt = analysis.battery(power)
    tips = analysis.recommend(power, fraction, status, batt)
    history = await get_power_history(session, history_limit)
    return PowerReport(
        generated_at=datetime.now(UTC),
        source=source,
        power=power,
        headroom_mw=spare,
        headroom_percent=fraction,
        status=status,
        battery=batt,
        recommendations=tips,
        history=history,
    )
