"""Shared FastAPI dependencies (settings, DB session, shared singletons)."""

from __future__ import annotations

from fastapi import Request

from app.config.settings import Settings, get_settings
from app.database.engine import get_session
from app.services.event_bus import EventBus


def get_event_bus(request: Request) -> EventBus:
    """Return the application-wide event bus stored on app state."""
    bus: EventBus = request.app.state.event_bus
    return bus


__all__ = ["get_settings", "get_session", "get_event_bus", "Settings"]
