"""User authentication: registration, login, and stateless session tokens.

Passwords are hashed with PBKDF2 (reusing :func:`app.services.admin_auth.hash_password`).
Session tokens are stateless HMAC-signed strings carrying the user id and an
expiry: ``base64url(user_id|expiry).hmac_sha256(secret, payload)`` — the same
scheme the admin panel already uses, so no new dependencies. The signing secret
comes from ``SPIFFCO_AUTH_SESSION_SECRET`` (falling back to the admin session
secret), or is generated per process (tokens then reset on restart).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from app.errors import ConflictError, UnauthorizedError
from app.models.user import STATUS_ACTIVE, STATUS_PENDING, User
from app.schemas.auth import SessionInfo
from app.services.admin_auth import hash_password
from app.services.permissions import preset_permissions


class AuthService:
    """Registers users and issues/verifies DB-backed session tokens."""

    def __init__(self, settings: Settings) -> None:
        self._ttl_seconds = settings.auth_session_ttl_minutes * 60
        secret = (
            settings.auth_session_secret
            or settings.admin_session_secret
            or secrets.token_hex(32)
        )
        self._secret = secret.encode()

    async def register(self, session: AsyncSession, username: str, password: str) -> User:
        """Create a pending account. Raises :class:`ConflictError` if taken."""
        existing = await session.scalar(select(User).where(User.username == username))
        if existing is not None:
            raise ConflictError("That username is already taken")
        user = User(
            username=username,
            password_hash=hash_password(password),
            status=STATUS_PENDING,
            role="viewer",
            permissions_json="[]",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

    async def authenticate(
        self, session: AsyncSession, username: str, password: str
    ) -> SessionInfo:
        """Verify credentials for an active account and return a session.

        Raises:
            UnauthorizedError: on unknown user, wrong password, or an account
                that is still pending approval or has been disabled.
        """
        user = await session.scalar(select(User).where(User.username == username))
        # Verify the password even when the user is missing/inactive so timing
        # does not reveal which usernames exist or are approved.
        password_ok = _verify_password(password, user.password_hash if user else None)
        if user is None or not password_ok:
            raise UnauthorizedError("Invalid username or password")
        if user.status != STATUS_ACTIVE:
            raise UnauthorizedError(
                "Your account is awaiting approval"
                if user.status == STATUS_PENDING
                else "Your account has been disabled"
            )
        return self.issue_session(user)

    def issue_session(self, user: User) -> SessionInfo:
        """Mint a fresh session token for an already-authenticated *user*."""
        expiry = int(time.time()) + self._ttl_seconds
        payload = base64.urlsafe_b64encode(f"{user.id}|{expiry}".encode()).decode()
        signature = hmac.new(self._secret, payload.encode(), hashlib.sha256).hexdigest()
        return SessionInfo(
            token=f"{payload}.{signature}",
            username=user.username,
            role=user.role,
            permissions=user.permissions,
            is_superuser=user.is_superuser,
            expires_at=datetime.fromtimestamp(expiry, tz=UTC),
        )

    def parse_token(self, token: str) -> int:
        """Return the user id for a valid, unexpired token.

        Raises:
            UnauthorizedError: on a missing, malformed, forged, or expired token.
        """
        try:
            payload, signature = token.split(".")
            expected = hmac.new(self._secret, payload.encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(signature, expected):
                raise ValueError("bad signature")
            user_id, expiry = base64.urlsafe_b64decode(payload.encode()).decode().split("|")
            if time.time() > int(expiry):
                raise ValueError("expired")
            return int(user_id)
        except (ValueError, TypeError) as exc:
            raise UnauthorizedError("Session is invalid or expired") from exc

    async def load_active_user(self, session: AsyncSession, token: str) -> User:
        """Resolve *token* to its active user, or raise ``UnauthorizedError``."""
        user_id = self.parse_token(token)
        user = await session.get(User, user_id)
        if user is None or user.status != STATUS_ACTIVE:
            raise UnauthorizedError("Session is invalid or expired")
        return user

    async def ensure_superuser(
        self, session: AsyncSession, username: str, password_hash: str
    ) -> None:
        """Seed/refresh the owner account from env credentials on startup.

        The superuser is always active with every permission and cannot be
        disabled or deleted. Its credentials track ``SPIFFCO_ADMIN_PASSWORD``
        (or ``_HASH``) so the env stays the source of truth for the owner login.

        Args:
            password_hash: A PBKDF2 hash string (from :func:`hash_password` or
                ``SPIFFCO_ADMIN_PASSWORD_HASH``).
        """
        user = await session.scalar(select(User).where(User.username == username))
        if user is None:
            user = User(username=username)
            session.add(user)
        user.password_hash = password_hash
        user.status = STATUS_ACTIVE
        user.role = "admin"
        user.is_superuser = True
        user.permissions = preset_permissions("admin")
        await session.commit()


def _verify_password(password: str, encoded: str | None) -> bool:
    """Verify *password* against a stored PBKDF2 hash (constant-ish time)."""
    from app.services.admin_auth import _verify_hash

    if not encoded:
        # Run a throwaway verification so the no-user path costs the same.
        _verify_hash(password, hash_password(password))
        return False
    return _verify_hash(password, encoded)
