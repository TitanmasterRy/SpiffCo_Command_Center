"""Schemas for the factory planner: grid layouts, plans, versions, summaries.

A *plan* owns a mutable current layout plus an append-only history of
:class:`PlanVersion` snapshots — every save records a new version so a layout can
be reverted. A *layout* is a grid plus a set of building *placements*; the
service validates placements (in-bounds, non-overlapping, known building, legal
clock) and derives a :class:`PlanSummary` (power draw, build cost, machine
counts) that seeds the Phase 5 production planner's shopping list.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

Rotation = int  # one of 0, 90, 180, 270 — validated in Placement.

# Minimum / maximum overclock as a fraction (25 % .. 250 %).
MIN_CLOCK = 0.01
MAX_CLOCK = 2.5


class GridSpec(BaseModel):
    """Planning grid dimensions in cells (one cell = ``cell_cm`` centimeters)."""

    width: int = Field(ge=1, le=1000, description="Grid width in cells (x axis)")
    length: int = Field(ge=1, le=1000, description="Grid length in cells (y axis)")
    cell_cm: int = Field(default=100, ge=1, le=10000, description="Centimeters per cell")


class Placement(BaseModel):
    """A single building placed on the grid.

    ``x``/``y`` are the top-left cell of the building's footprint. ``rotation``
    of 90/270 swaps the footprint's width and length.
    """

    id: str = Field(min_length=1, max_length=64, description="Client-unique placement id")
    building: str = Field(min_length=1, max_length=64, description="Building id (buildings.json)")
    x: int = Field(ge=0, description="Top-left cell, x axis")
    y: int = Field(ge=0, description="Top-left cell, y axis")
    rotation: Rotation = Field(default=0)
    clock: float = Field(default=1.0, ge=MIN_CLOCK, le=MAX_CLOCK, description="Clock fraction")

    def model_post_init(self, _context: object) -> None:  # noqa: D401 - pydantic hook
        """Reject rotations that are not axis-aligned multiples of 90°."""
        if self.rotation not in (0, 90, 180, 270):
            raise ValueError("rotation must be one of 0, 90, 180, 270")


class Layout(BaseModel):
    """A grid plus its building placements — the editable heart of a plan."""

    grid: GridSpec
    placements: list[Placement] = Field(default_factory=list)


class PlanSummary(BaseModel):
    """Derived rollup for a layout: power, cost, and machine counts."""

    total_power_mw: float = Field(description="Sum of power draw across placements")
    machine_count: int
    machine_counts: dict[str, int] = Field(
        default_factory=dict, description="building id -> count"
    )
    build_cost: dict[str, int] = Field(
        default_factory=dict, description="item id -> total quantity"
    )


class PlanCreate(BaseModel):
    """Payload to create a plan (layout optional; empty grid default)."""

    name: str = Field(min_length=1, max_length=128)
    description: str = Field(default="", max_length=2000)
    layout: Layout | None = None


class PlanUpdate(BaseModel):
    """Payload to update a plan. A new layout records a new version."""

    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=2000)
    layout: Layout | None = None
    comment: str = Field(default="", max_length=256, description="Version comment when layout set")


class PlanSummaryInfo(BaseModel):
    """Lightweight plan record for list views (no layout body)."""

    id: int
    name: str
    description: str
    version: int
    created_at: datetime
    updated_at: datetime


class FactoryPlan(PlanSummaryInfo):
    """A full plan: metadata, current layout, and its derived summary."""

    layout: Layout
    summary: PlanSummary


class PlanVersion(BaseModel):
    """One historical snapshot of a plan's layout."""

    version: int
    comment: str
    created_at: datetime
    layout: Layout


class PlanExport(BaseModel):
    """Portable plan document for download / import (no server ids)."""

    name: str
    description: str = ""
    layout: Layout
    exported_at: datetime | None = None


class Footprint(BaseModel):
    """Building footprint in cells (before rotation)."""

    width: int
    length: int


class BuildingInfo(BaseModel):
    """Game-data building record served to the planner frontend."""

    id: str
    name: str
    category: str
    power_mw: float
    inputs: int
    outputs: int
    footprint: Footprint
    build_cost: dict[str, int] = Field(default_factory=dict)
