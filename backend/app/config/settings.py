"""Typed application settings.

All configuration is environment-driven with the ``SPIFFCO_`` prefix and can also
be supplied via a ``.env`` file in the working directory. Access settings only
through :func:`get_settings` so tests can override them cleanly.
"""

from __future__ import annotations

from enum import Enum
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Deployment environment the app is running in."""

    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TEST = "test"


class Settings(BaseSettings):
    """Central application settings (env prefix ``SPIFFCO_``)."""

    model_config = SettingsConfigDict(
        env_prefix="SPIFFCO_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_name: str = "SpiffCo Command Center"
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = True

    # API server
    host: str = "127.0.0.1"
    port: int = 8000
    cors_origins: list[str] = Field(default=["http://localhost:5173"])

    # Database
    database_url: str = "sqlite+aiosqlite:///./spiffco.db"

    # Logging
    log_level: str = "INFO"
    log_file: str = ""

    # Ficsit Remote Monitoring (Phase 11). When disabled (default), the app runs
    # on the simulated providers. When enabled, it polls the FRM mod and falls
    # back to simulation if the mod is unreachable at startup.
    frm_enabled: bool = False
    frm_base_url: str = "http://localhost:8080"
    frm_poll_interval_seconds: float = 5.0
    frm_timeout_seconds: float = 5.0
    frm_cache_ttl_seconds: float = 2.0

    # Offline mode (Phase 12): maximum accepted save-file upload size.
    save_max_upload_mb: int = 100

    # Optional path to a built frontend (Vite ``dist/``). When set and present,
    # the API also serves the SPA from the same origin (single-process deploy,
    # e.g. Fly.io). Empty in dev, where Vite serves the frontend separately.
    static_dir: str = ""

    # Background scheduler (periodic refresh/history jobs). Disabled in tests so
    # background DB writes never race request handlers on the shared connection.
    scheduler_enabled: bool = True

    # User authentication (login + account approval + per-user permissions).
    # When enabled, all data endpoints require a valid session and the frontend
    # gates pages by permission. Disabled by default so a solo LAN setup runs
    # without login. auth_allow_registration exposes the public sign-up form.
    auth_enabled: bool = False
    auth_allow_registration: bool = True
    auth_session_ttl_minutes: int = 720
    # HMAC secret for user session tokens; falls back to admin_session_secret,
    # then to a per-process random value (sessions reset on restart).
    auth_session_secret: str = ""
    # Legacy single-token auth (unused by the current app).
    auth_token: str = ""

    # Admin panel (Phase 13). Login is disabled until a password (or hash) is
    # set — the panel fails closed instead of shipping a default credential.
    # admin_password_hash (pbkdf2, from app.services.admin_auth.hash_password)
    # wins over the plaintext admin_password when both are set.
    admin_username: str = "admin"
    admin_password: str = ""
    admin_password_hash: str = ""
    # HMAC secret for session tokens; random per process when empty (sessions
    # then reset on restart).
    admin_session_secret: str = ""
    admin_session_ttl_minutes: int = 480
    # Game-side command endpoint (the SpiffCoBridge companion mod). When empty,
    # cheat actions are simulated locally — FRM telemetry cannot execute them.
    # The token is sent as ``X-SpiffCo-Token`` and must match the bridge's
    # configured AuthToken (both empty = no auth, LAN-trusted setups only).
    admin_command_url: str = ""
    admin_command_token: str = ""

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        """Allow a comma-separated string for CORS origins in env vars."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("log_level")
    @classmethod
    def _normalize_log_level(cls, value: str) -> str:
        """Uppercase and validate the log level name."""
        level = value.upper()
        if level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError(f"invalid log level: {value!r}")
        return level


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings instance (cached).

    Tests can call ``get_settings.cache_clear()`` after patching the environment
    to get a fresh instance.
    """
    return Settings()
