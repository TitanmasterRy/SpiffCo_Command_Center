"""User accounts with approval status and per-user permissions."""

from __future__ import annotations

import json

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

#: Account lifecycle states.
STATUS_PENDING = "pending"
STATUS_ACTIVE = "active"
STATUS_DISABLED = "disabled"


class User(Base, TimestampMixin):
    """A site user. New sign-ups start ``pending`` until an admin approves them.

    ``permissions`` stores the effective permission keys as a JSON array. The
    ``role`` column is a convenience label (the preset the admin started from);
    authorization always consults the explicit permission list.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default=STATUS_PENDING, nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="viewer", nullable=False)
    permissions_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    # The seeded owner account (from SPIFFCO_ADMIN_PASSWORD): always active with
    # every permission, and protected from disabling or deletion.
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    @property
    def permissions(self) -> list[str]:
        """Effective permission keys (superusers implicitly hold all)."""
        try:
            values = json.loads(self.permissions_json)
        except (ValueError, TypeError):
            return []
        return [str(v) for v in values] if isinstance(values, list) else []

    @permissions.setter
    def permissions(self, value: list[str]) -> None:
        self.permissions_json = json.dumps(list(value))

    def has_permission(self, key: str) -> bool:
        """True if this user may exercise permission *key*."""
        return self.is_superuser or key in self.permissions
