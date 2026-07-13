"""Power endpoints: grid report with headroom, battery, and recommendations."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.power import service as power_service
from app.schemas.power import PowerReport
from app.services.game_state import GameStateService

router = APIRouter(prefix="/power", tags=["power"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]
LimitQuery = Annotated[int, Query(ge=1, le=1000)]


def _game_state(request: Request) -> GameStateService:
    service: GameStateService = request.app.state.game_state
    return service


@router.get("", response_model=PowerReport)
async def power_report(
    request: Request, session: SessionDep, history: LimitQuery = 120
) -> PowerReport:
    """Grid stats + headroom/battery analysis, recommendations, and history."""
    snapshot = _game_state(request).latest
    return await power_service.build_report(session, snapshot.power, snapshot.source, history)
