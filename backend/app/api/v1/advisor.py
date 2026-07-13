"""Advisor endpoint: ranked, explained findings from live game state."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.advisors import service as advisor_service
from app.logistics.service import LogisticsService
from app.schemas.advisor import AdvisorReport
from app.services.game_state import GameStateService

router = APIRouter(prefix="/advisor", tags=["advisor"])


@router.get("", response_model=AdvisorReport)
async def advisor_report(request: Request) -> AdvisorReport:
    """Ranked bottleneck/shortage/power findings with explanations and fixes."""
    game_state: GameStateService = request.app.state.game_state
    logistics: LogisticsService = request.app.state.logistics
    return advisor_service.build_report(game_state.latest, logistics.latest)
