"""Schemas for the blueprint library: entries, filters, stats, import/export."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class BlueprintIn(BaseModel):
    """Payload to create a blueprint."""

    name: str = Field(min_length=1, max_length=128)
    description: str = Field(default="", max_length=2000)
    category: str = Field(default="general", min_length=1, max_length=64)
    tags: list[str] = Field(default_factory=list)
    favorite: bool = False
    data: dict[str, Any] = Field(default_factory=dict, description="Reusable blueprint payload")


class BlueprintUpdate(BaseModel):
    """Partial update; only provided fields change."""

    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=2000)
    category: str | None = Field(default=None, min_length=1, max_length=64)
    tags: list[str] | None = None
    favorite: bool | None = None
    data: dict[str, Any] | None = None


class BlueprintSummary(BaseModel):
    """Lightweight library-card record (no ``data`` body)."""

    id: int
    name: str
    description: str
    category: str
    tags: list[str]
    favorite: bool
    created_at: datetime
    updated_at: datetime


class Blueprint(BlueprintSummary):
    """A full blueprint including its reusable payload."""

    data: dict[str, Any]


class BlueprintExport(BaseModel):
    """Portable blueprint document (no server ids)."""

    name: str
    description: str = ""
    category: str = "general"
    tags: list[str] = Field(default_factory=list)
    data: dict[str, Any] = Field(default_factory=dict)
    exported_at: datetime | None = None


class BlueprintStats(BaseModel):
    """Library rollup: totals and counts by category / tag."""

    total: int
    favorites: int
    by_category: dict[str, int]
    by_tag: dict[str, int]
