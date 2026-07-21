"""Username/password authentication for the admin panel.

Stateless HMAC-signed session tokens (stdlib only, no new dependencies):
``base64url(username|expiry)|hmac_sha256(secret, payload)``. The signing secret
comes from ``SPIFFCO_ADMIN_SESSION_SECRET`` or is generated per process (tokens
then expire on restart, which is acceptable for a self-hosted admin panel).

Passwords are configured via ``SPIFFCO_ADMIN_PASSWORD`` (plaintext, convenient
for self-hosting) or ``SPIFFCO_ADMIN_PASSWORD_HASH`` (PBKDF2, preferred — the
hash wins when both are set). If neither is set, login is disabled entirely:
the panel fails closed rather than shipping a default credential.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
from datetime import UTC, datetime

from app.config.settings import Settings
from app.errors import UnauthorizedError
from app.schemas.admin import SessionInfo

_HASH_PREFIX = "pbkdf2_sha256"
_PBKDF2_ITERATIONS = 600_000


def hash_password(password: str, *, iterations: int = _PBKDF2_ITERATIONS) -> str:
    """Return a PBKDF2 hash string suitable for ``SPIFFCO_ADMIN_PASSWORD_HASH``."""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return f"{_HASH_PREFIX}${iterations}${salt.hex()}${digest.hex()}"


def _verify_hash(password: str, encoded: str) -> bool:
    """Check *password* against a ``pbkdf2_sha256$iter$salt$hash`` string."""
    try:
        prefix, iterations, salt_hex, digest_hex = encoded.split("$")
        if prefix != _HASH_PREFIX:
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


class AdminAuthService:
    """Issues and verifies admin session tokens against configured credentials."""

    def __init__(self, settings: Settings) -> None:
        self._username = settings.admin_username
        self._password = settings.admin_password
        self._password_hash = settings.admin_password_hash
        self._ttl_seconds = settings.admin_session_ttl_minutes * 60
        self._secret = (settings.admin_session_secret or secrets.token_hex(32)).encode()

    @property
    def configured(self) -> bool:
        """True when a password (or hash) has been set."""
        return bool(self._password or self._password_hash)

    def login(self, username: str, password: str) -> SessionInfo:
        """Validate credentials and return a fresh session.

        Raises:
            UnauthorizedError: if auth is unconfigured or credentials are wrong.
        """
        if not self.configured:
            raise UnauthorizedError(
                "Admin panel is not configured. Set SPIFFCO_ADMIN_PASSWORD "
                "(or SPIFFCO_ADMIN_PASSWORD_HASH) on the backend."
            )
        user_ok = hmac.compare_digest(username.encode(), self._username.encode())
        if self._password_hash:
            pass_ok = _verify_hash(password, self._password_hash)
        else:
            pass_ok = hmac.compare_digest(password.encode(), self._password.encode())
        if not (user_ok and pass_ok):
            raise UnauthorizedError("Invalid username or password")

        expiry = int(time.time()) + self._ttl_seconds
        payload = base64.urlsafe_b64encode(f"{username}|{expiry}".encode()).decode()
        signature = hmac.new(self._secret, payload.encode(), hashlib.sha256).hexdigest()
        return SessionInfo(
            token=f"{payload}.{signature}",
            username=username,
            expires_at=datetime.fromtimestamp(expiry, tz=UTC),
        )

    def verify(self, token: str) -> str:
        """Return the username for a valid, unexpired token.

        Raises:
            UnauthorizedError: on a missing, malformed, forged, or expired token.
        """
        return self.inspect(token).username

    def inspect(self, token: str) -> SessionInfo:
        """Validate a token and return its session details.

        Raises:
            UnauthorizedError: on a missing, malformed, forged, or expired token.
        """
        try:
            payload, signature = token.split(".")
            expected = hmac.new(self._secret, payload.encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(signature, expected):
                raise ValueError("bad signature")
            username, expiry = base64.urlsafe_b64decode(payload.encode()).decode().split("|")
            if time.time() > int(expiry):
                raise ValueError("expired")
        except (ValueError, TypeError) as exc:
            raise UnauthorizedError("Admin session is invalid or expired") from exc
        return SessionInfo(
            token=token,
            username=username,
            expires_at=datetime.fromtimestamp(int(expiry), tz=UTC),
        )
