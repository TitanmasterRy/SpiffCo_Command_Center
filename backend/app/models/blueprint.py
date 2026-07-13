"""Persisted blueprint library entries."""

from __future__ import annotations

from typing import Any

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.models.base import Base, TimestampMixin


class Blueprint(Base, TimestampMixin):
    """A reusable, categorized blueprint fragment (layout / recipe / notes)."""

    __tablename__ = "blueprints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(64), default="general", index=True)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
