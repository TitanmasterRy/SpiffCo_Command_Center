"""Public schemas for user authentication and account management."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Role = Literal["viewer", "operator", "admin"]
Status = Literal["pending", "active", "disabled"]

_USERNAME = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
_PASSWORD = Field(min_length=8, max_length=256)


class Credentials(BaseModel):
    """Username/password submitted to register a new account (strict rules)."""

    username: str = _USERNAME
    password: str = _PASSWORD


class LoginCredentials(BaseModel):
    """Credentials submitted to log in (no complexity rules — just non-empty).

    Enforcing the sign-up rules here would leak them and turn a wrong password
    into a 422 instead of a clean 401.
    """

    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class AuthConfig(BaseModel):
    """Public auth configuration the frontend reads on boot."""

    enabled: bool
    allow_registration: bool


class PermissionInfo(BaseModel):
    """One selectable permission (key + human label) for the admin UI."""

    key: str
    label: str


class AuthCatalog(BaseModel):
    """The set of assignable permissions and role presets."""

    permissions: list[PermissionInfo]
    roles: dict[str, list[str]]


class SessionInfo(BaseModel):
    """An authenticated session plus the caller's effective permissions."""

    token: str
    username: str
    role: str
    permissions: list[str]
    is_superuser: bool
    expires_at: datetime


class UserSummary(BaseModel):
    """A user row for the admin management table."""

    id: int
    username: str
    status: Status
    role: str
    permissions: list[str]
    is_superuser: bool
    created_at: datetime


class RegisterResult(BaseModel):
    """Response to a sign-up request (no token — approval is pending)."""

    status: Status
    message: str


class ApproveRequest(BaseModel):
    """Approve a pending account with an initial role and permissions."""

    role: Role = "viewer"
    permissions: list[str] | None = None


class UpdateUserRequest(BaseModel):
    """Patch a user's role, permissions, or status."""

    role: Role | None = None
    permissions: list[str] | None = None
    status: Status | None = None
