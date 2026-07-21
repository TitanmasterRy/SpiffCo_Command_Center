"""Shared FastAPI dependencies (settings, DB session, shared singletons)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings, get_settings
from app.database.engine import get_session
from app.errors import ForbiddenError, UnauthorizedError
from app.models.user import STATUS_ACTIVE, User
from app.services.auth import AuthService
from app.services.event_bus import EventBus


def get_event_bus(request: Request) -> EventBus:
    """Return the application-wide event bus stored on app state."""
    bus: EventBus = request.app.state.event_bus
    return bus


def get_auth_service(request: Request) -> AuthService:
    """Return the application-wide authentication service."""
    service: AuthService = request.app.state.auth
    return service


def _local_superuser() -> User:
    """A synthetic all-access user used when auth is disabled (solo LAN mode)."""
    return User(username="local", status=STATUS_ACTIVE, role="admin", is_superuser=True)


async def get_current_user(
    session: Annotated[AsyncSession, Depends(get_session)],
    auth: Annotated[AuthService, Depends(get_auth_service)],
    authorization: Annotated[str, Header()] = "",
) -> User:
    """Resolve the caller's active user, or raise ``UnauthorizedError``.

    When ``SPIFFCO_AUTH_ENABLED`` is false the app runs without login and every
    request is treated as a local all-access superuser, preserving the original
    single-user behavior.
    """
    if not get_settings().auth_enabled:
        return _local_superuser()
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise UnauthorizedError("Authentication required")
    return await auth.load_active_user(session, token)


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_permission(permission: str) -> Callable[[User], Awaitable[User]]:
    """Build a dependency that requires the caller to hold *permission*."""

    async def dependency(user: CurrentUser) -> User:
        if not user.has_permission(permission):
            raise ForbiddenError(
                f"You do not have permission to perform this action ({permission})"
            )
        return user

    return dependency


__all__ = [
    "get_settings",
    "get_session",
    "get_event_bus",
    "get_auth_service",
    "get_current_user",
    "require_permission",
    "CurrentUser",
    "Settings",
]
