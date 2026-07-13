"""Schemas for logistics: transport tiers, network nodes/routes, live trains.

The logistics *network* is a set of :class:`LogisticsNode` endpoints joined by
:class:`LogisticsRoute` edges, each carrying an item at some throughput against a
tier capacity. ``utilization`` is derived (throughput / capacity) so over-capacity
routes can be flagged. Trains stream live positions on WS topic
``logistics.trains``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, computed_field

from app.schemas.world import Position

LogisticsMode = Literal["belt", "pipe", "train", "truck", "drone"]
NodeType = Literal["station", "factory", "port"]


class BeltTier(BaseModel):
    """A conveyor belt or pipeline tier with its max rate (items or m³/min)."""

    id: str
    name: str
    rate: float


class VehicleTier(BaseModel):
    """A logistics vehicle with its carrying/power characteristics."""

    id: str
    name: str
    capacity_slots: int | None = None
    power_mw: float | None = None
    fuel: str | None = None


class TransportData(BaseModel):
    """The full static transport catalog served to the frontend."""

    belts: list[BeltTier]
    pipes: list[BeltTier]
    vehicles: list[VehicleTier]


class LogisticsNode(BaseModel):
    """An endpoint in the logistics network (station, factory, or port)."""

    id: str
    name: str
    type: NodeType
    position: Position


class LogisticsRoute(BaseModel):
    """A directed connection carrying one item between two nodes."""

    id: str
    name: str
    mode: LogisticsMode
    tier: str = Field(description="Transport tier id, e.g. belt-mk5 / pipe-mk2 / drone")
    item: str
    throughput_per_min: float = Field(ge=0)
    capacity_per_min: float = Field(gt=0)
    from_node: str
    to_node: str

    @computed_field  # type: ignore[prop-decorator]
    @property
    def utilization(self) -> float:
        """Fraction of capacity in use (>1 means over capacity)."""
        return round(self.throughput_per_min / self.capacity_per_min, 4)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def over_capacity(self) -> bool:
        """True when demanded throughput exceeds the route's capacity."""
        return self.throughput_per_min > self.capacity_per_min


class TrainInfo(BaseModel):
    """A train and its live position along a line."""

    id: str
    name: str
    line: str
    position: Position
    loaded_item: str | None = None


class LogisticsSummary(BaseModel):
    """Rolled-up network statistics."""

    route_count: int
    node_count: int
    over_capacity_routes: list[str] = Field(default_factory=list)
    throughput_by_mode: dict[str, float] = Field(default_factory=dict)
    max_utilization: float = 0.0


class LogisticsSnapshot(BaseModel):
    """The full logistics network plus live trains and a summary."""

    generated_at: datetime
    source: Literal["simulation", "frm"]
    nodes: list[LogisticsNode]
    routes: list[LogisticsRoute]
    trains: list[TrainInfo]
    summary: LogisticsSummary
