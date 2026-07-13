"""Schemas for offline mode: parsed-save summary and data-source status."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.offline.building_map import Category


class BuildingCount(BaseModel):
    """How many of one building class a save contains."""

    class_name: str = Field(description="Satisfactory Build_..._C class name")
    name: str
    category: Category
    count: int
    power_mw: float = Field(description="Nominal per-unit power (consumed, or generated)")


class SaveSummary(BaseModel):
    """Human-facing summary of a parsed save file."""

    session_name: str
    map_name: str
    build_version: int
    play_duration_seconds: int
    saved_at: datetime | None
    total_buildings: int = Field(description="Catalogued buildings identified in the save")
    machine_count: int = Field(description="Production + extraction machines")
    generator_count: int
    estimated_power_capacity_mw: float
    estimated_power_consumption_mw: float
    buildings: list[BuildingCount]


class OfflineStatus(BaseModel):
    """Which data source is live and, if a save is loaded, its summary."""

    active: bool = Field(description="True when a save file is the live data source")
    source: Literal["simulation", "frm", "save"]
    save: SaveSummary | None = None
