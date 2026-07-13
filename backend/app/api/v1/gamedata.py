"""Static game-data endpoints (single source of truth for the frontend)."""

from __future__ import annotations

from fastapi import APIRouter

from app.logistics.data import load_transport
from app.planner.gamedata import load_buildings
from app.power.data import load_power_buildings
from app.production.data import load_items, load_recipes
from app.schemas.logistics import TransportData
from app.schemas.planner import BuildingInfo
from app.schemas.power import PowerBuildingInfo
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


@router.get("/transport", response_model=TransportData)
async def transport() -> TransportData:
    """Belt/pipe tiers and logistics vehicles with their capacities."""
    return load_transport()


@router.get("/power", response_model=list[PowerBuildingInfo])
async def list_power_buildings() -> list[PowerBuildingInfo]:
    """Generators and power storage with output, fuel, and capacity."""
    return list(load_power_buildings())
