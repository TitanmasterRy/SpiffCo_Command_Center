"""FRM connector interface.

Phase 11 implements discovery, polling, WebSocket streaming, reconnection,
health monitoring, and caching behind this interface. Phase 1 ships the
contract so services, workers, and tests can depend on it now.

Design rules (see docs/ARCHITECTURE.md):

- Raw FRM payloads never leave this package; every read method returns
  normalized ``app.schemas`` models.
- The connector publishes normalized snapshots on the event bus
  (``frm.<domain>`` topics) instead of being polled by consumers.
"""

from __future__ import annotations

import logging
from enum import Enum

from app.config.settings import Settings
from app.errors import UpstreamUnavailableError
from app.services.event_bus import EventBus

logger = logging.getLogger(__name__)


class ConnectionState(str, Enum):
    """Lifecycle states of the FRM connection."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class FrmConnector:
    """Client for a Ficsit Remote Monitoring endpoint.

    Args:
        settings: Application settings (FRM base URL, poll interval, timeout).
        bus: Event bus on which normalized snapshots are published.
    """

    def __init__(self, settings: Settings, bus: EventBus) -> None:
        self._settings = settings
        self._bus = bus
        self._state = ConnectionState.DISCONNECTED

    @property
    def state(self) -> ConnectionState:
        """Current connection state."""
        return self._state

    async def start(self) -> None:
        """Begin connecting and polling/streaming. Implemented in Phase 11."""
        raise UpstreamUnavailableError(
            "FRM integration is not implemented yet (arrives in Phase 11)"
        )

    async def stop(self) -> None:
        """Stop polling and close connections. Implemented in Phase 11."""
        self._state = ConnectionState.DISCONNECTED
