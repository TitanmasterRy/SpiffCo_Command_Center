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

    # Ficsit Remote Monitoring (used from Phase 11 onwards)
    frm_base_url: str = "http://localhost:8080"
    frm_poll_interval_seconds: float = 5.0
    frm_timeout_seconds: float = 5.0

    # Optional authentication
    auth_enabled: bool = False
    auth_token: str = ""

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
