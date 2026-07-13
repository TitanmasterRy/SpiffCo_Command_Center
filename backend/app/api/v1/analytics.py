"""Analytics endpoints: aggregated power and production KPIs over history."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import service as analytics_service
from app.api.deps import get_session
from app.schemas.analytics import AnalyticsSummary, ProductionAnalytics

router = APIRouter(prefix="/analytics", tags=["analytics"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]
LimitQuery = Annotated[int, Query(ge=1, le=2000)]


@router.get("/summary", response_model=AnalyticsSummary)
async def analytics_summary(session: SessionDep, limit: LimitQuery = 240) -> AnalyticsSummary:
    """Power KPIs plus the busiest production lines over the recent samples."""
    return await analytics_service.summary(session, limit)


@router.get("/production/{item}", response_model=ProductionAnalytics)
async def production_analytics(
    item: str, session: SessionDep, limit: LimitQuery = 240
) -> ProductionAnalytics:
    """Analytics for one item's production history (404 if none)."""
    return await analytics_service.production_analytics(session, item, limit)
