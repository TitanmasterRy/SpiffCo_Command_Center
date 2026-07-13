"""Schemas for the world map: features, players, custom markers."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

FeatureType = Literal[
    "factory",
    "resource_node",
    "resource_well",
    "geyser",
    "power_plant",
    "train_station",
    "drone_port",
    "truck_station",
    "artifact",
    "collectible",
    "wreck",
]


class Position(BaseModel):
    """Game-world position in centimeters (Unreal units); +x east, +y south."""

    x: float
    y: float
    z: float = 0


class MapFeature(BaseModel):
    """A world object shown on the map."""

    id: str
    type: FeatureType
    name: str
    position: Position
    meta: dict[str, str | float | int] = Field(default_factory=dict)
    collected: bool | None = Field(
        default=None, description="Pickups only: already collected by a player"
    )
    occupied: bool | None = Field(
        default=None, description="Resource nodes only: an extractor is installed"
    )


class PlayerInfo(BaseModel):
    """A player and their live position."""

    id: str
    name: str
    position: Position
    online: bool = True


class WorldSnapshot(BaseModel):
    """Static features plus live player positions."""

    generated_at: datetime
    source: Literal["simulation", "frm", "save"]
    players: list[PlayerInfo]
    features: list[MapFeature]


class CustomMarkerIn(BaseModel):
    """User-created marker payload."""

    name: str = Field(min_length=1, max_length=128)
    icon: str = Field(default="pin", max_length=32)
    color: str = Field(default="#9085e9", pattern=r"^#[0-9a-fA-F]{6}$")
    position: Position
    notes: str = Field(default="", max_length=2000)


class CustomMarker(CustomMarkerIn):
    """A persisted custom marker."""

    id: int
