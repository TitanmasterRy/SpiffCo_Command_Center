"""Static game-data endpoints (single source of truth for the frontend)."""

from __future__ import annotations

from fastapi import APIRouter

from app.planner.gamedata import load_buildings
from app.schemas.planner import BuildingInfo

router = APIRouter(prefix="/gamedata", tags=["gamedata"])


@router.get("/buildings", response_model=list[BuildingInfo])
async def list_buildings() -> list[BuildingInfo]:
    """Production/extraction buildings with footprints and build costs."""
    return list(load_buildings())
