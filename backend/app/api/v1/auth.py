"""Authentication endpoints: registration, login, and session restore."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_auth_service, get_session, get_settings
from app.errors import ForbiddenError
from app.schemas.auth import (
    AuthCatalog,
    AuthConfig,
    Credentials,
    LoginCredentials,
    PermissionInfo,
    RegisterResult,
    SessionInfo,
)
from app.services.auth import AuthService
from app.services.permissions import ALL_PERMISSIONS, ROLE_PRESETS

router = APIRouter(prefix="/auth", tags=["auth"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]
AuthDep = Annotated[AuthService, Depends(get_auth_service)]


@router.get("/config", response_model=AuthConfig)
async def auth_config() -> AuthConfig:
    """Public flags the frontend reads on boot to decide whether to gate the UI."""
    settings = get_settings()
    return AuthConfig(
        enabled=settings.auth_enabled,
        allow_registration=settings.auth_allow_registration,
    )


@router.get("/catalog", response_model=AuthCatalog)
async def auth_catalog() -> AuthCatalog:
    """The assignable permissions and role presets (for the admin users tab)."""
    return AuthCatalog(
        permissions=[PermissionInfo(key=k, label=v) for k, v in ALL_PERMISSIONS.items()],
        roles=dict(ROLE_PRESETS),
    )


@router.post("/register", response_model=RegisterResult, status_code=201)
async def register(body: Credentials, session: SessionDep, auth: AuthDep) -> RegisterResult:
    """Request a new account. It stays pending until an admin approves it."""
    settings = get_settings()
    if not settings.auth_allow_registration:
        raise ForbiddenError("Account registration is disabled")
    user = await auth.register(session, body.username, body.password)
    return RegisterResult(
        status=user.status,
        message="Your account request was submitted and is awaiting approval.",
    )


@router.post("/login", response_model=SessionInfo)
async def login(body: LoginCredentials, session: SessionDep, auth: AuthDep) -> SessionInfo:
    """Exchange username/password for a session token."""
    return await auth.authenticate(session, body.username, body.password)


@router.get("/me", response_model=SessionInfo)
async def me(user: CurrentUser, auth: AuthDep) -> SessionInfo:
    """Return the current session (used by the frontend to restore state)."""
    return auth.issue_session(user)
