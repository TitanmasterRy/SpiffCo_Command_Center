"""Persisted factory plans and their append-only version history."""

from __future__ import annotations

from typing import Any

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.models.base import Base, TimestampMixin


class FactoryPlan(Base, TimestampMixin):
    """A factory layout plan; ``layout`` holds the current grid + placements."""

    __tablename__ = "factory_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    layout: Mapped[dict[str, Any]] = mapped_column(JSON)

    versions: Mapped[list[PlanVersion]] = relationship(
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="PlanVersion.version",
    )


class PlanVersion(Base, TimestampMixin):
    """An immutable snapshot of a plan's layout, created on every save."""

    __tablename__ = "plan_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("factory_plans.id", ondelete="CASCADE"))
    version: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str] = mapped_column(String(256), default="")
    layout: Mapped[dict[str, Any]] = mapped_column(JSON)

    plan: Mapped[FactoryPlan] = relationship(back_populates="versions")
