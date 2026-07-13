"""Logistics endpoints: network snapshot with throughput analysis."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.logistics.service import LogisticsService
from app.schemas.logistics import LogisticsSnapshot

router = APIRouter(prefix="/logistics", tags=["logistics"])


def _service(request: Request) -> LogisticsService:
    service: LogisticsService = request.app.state.logistics
    return service


@router.get("", response_model=LogisticsSnapshot)
async def logistics_snapshot(request: Request) -> LogisticsSnapshot:
    """Latest logistics network: nodes, routes (with utilization), and live
    trains. Trains also stream on WS topic ``logistics.trains``."""
    return _service(request).latest
