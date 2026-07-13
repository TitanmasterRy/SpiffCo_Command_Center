"""Static game-data endpoints (single source of truth for the frontend)."""

from __future__ import annotations

from fastapi import APIRouter

from app.planner.gamedata import load_buildings
from app.production.data import load_items, load_recipes
from app.schemas.planner import BuildingInfo
from app.schemas.production import ItemInfo, RecipeInfo

router = APIRouter(prefix="/gamedata", tags=["gamedata"])


@router.get("/buildings", response_model=list[BuildingInfo])
async def list_buildings() -> list[BuildingInfo]:
    """Production/extraction buildings with footprints and build costs."""
    return list(load_buildings())


@router.get("/recipes", response_model=list[RecipeInfo])
async def list_recipes() -> list[RecipeInfo]:
    """All recipes (base + alternates) with inputs/outputs per minute."""
    return list(load_recipes())


@router.get("/items", response_model=list[ItemInfo])
async def list_items() -> list[ItemInfo]:
    """All known game items."""
    return list(load_items())
