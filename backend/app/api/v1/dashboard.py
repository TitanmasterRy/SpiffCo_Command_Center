"""Dashboard endpoints: live snapshot and telemetry history."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.schemas.dashboard import (
    DashboardSnapshot,
    PowerHistoryPoint,
    ProductionHistoryPoint,
)
from app.services import game_state
from app.services.game_state import GameStateService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]
LimitQuery = Annotated[int, Query(ge=1, le=1000)]


def _service(request: Request) -> GameStateService:
    service: GameStateService = request.app.state.game_state
    return service


@router.get("", response_model=DashboardSnapshot)
async def snapshot(request: Request) -> DashboardSnapshot:
    """Latest dashboard snapshot (503 until the first refresh completes)."""
    return _service(request).latest


@router.get("/history/power", response_model=list[PowerHistoryPoint])
async def power_history(session: SessionDep, limit: LimitQuery = 120) -> list[PowerHistoryPoint]:
    """Recent power samples, oldest first."""
    return await game_state.get_power_history(session, limit)


@router.get("/history/production/{item}", response_model=list[ProductionHistoryPoint])
async def production_history(
    item: str, session: SessionDep, limit: LimitQuery = 120
) -> list[ProductionHistoryPoint]:
    """Recent production samples for one item, oldest first."""
    return await game_state.get_production_history(session, item, limit)
