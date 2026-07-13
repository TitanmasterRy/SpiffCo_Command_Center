"""FRM connector: background polling, normalization, and cached snapshots.

Polls the FRM mod on an interval, normalizes each response into internal schemas
(:mod:`app.connectors.frm.normalize`), and holds the latest dashboard/world/
logistics snapshots in memory. The synchronous provider protocol
(:meth:`snapshot`) is satisfied by returning these cached snapshots, so services
never block on HTTP. Connection-state changes publish on the ``frm.status`` topic.

Design rules (docs/ARCHITECTURE.md): raw FRM payloads never leave this package;
every consumer sees normalized ``app.schemas`` models.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from enum import StrEnum

from app.config.settings import Settings
from app.connectors.frm import normalize
from app.connectors.frm.client import FrmClient
from app.errors import UpstreamUnavailableError
from app.schemas.dashboard import DashboardSnapshot
from app.schemas.logistics import LogisticsSnapshot
from app.schemas.world import WorldSnapshot
from app.services.event_bus import EventBus

logger = logging.getLogger(__name__)


class ConnectionState(StrEnum):
    """Lifecycle states of the FRM connection."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class FrmConnector:
    """Polls FRM and exposes the latest normalized snapshots.

    Args:
        settings: Application settings (FRM base URL, poll interval, timeout).
        bus: Event bus on which connection-state changes are published.
        client: Optional pre-built client (used by tests); otherwise created
            from *settings*.
    """

    def __init__(
        self, settings: Settings, bus: EventBus, client: FrmClient | None = None
    ) -> None:
        self._settings = settings
        self._bus = bus
        self._client = client or FrmClient(
            settings.frm_base_url,
            timeout=settings.frm_timeout_seconds,
            cache_ttl=settings.frm_cache_ttl_seconds,
        )
        self._state = ConnectionState.DISCONNECTED
        self._task: asyncio.Task[None] | None = None
        self._dashboard: DashboardSnapshot | None = None
        self._world: WorldSnapshot | None = None
        self._logistics: LogisticsSnapshot | None = None

    @property
    def state(self) -> ConnectionState:
        """Current connection state."""
        return self._state

    def _set_state(self, state: ConnectionState) -> None:
        if state != self._state:
            self._state = state
            self._bus.publish("frm.status", {"state": state.value})
            logger.info("FRM connection state: %s", state.value)

    async def poll_once(self) -> None:
        """Fetch all endpoints once and refresh the cached snapshots.

        Raises:
            UpstreamUnavailableError: if any FRM request fails.
        """
        power = await self._client.get("getPower")
        factory = await self._client.get("getFactory")
        players = await self._client.get("getPlayer")
        nodes = await self._client.get("getResourceNode")
        stations = await self._client.get("getTrainStation")
        trains = await self._client.get("getTrains")
        self._dashboard = normalize.normalize_dashboard(power, factory)
        self._world = normalize.normalize_world(players, factory, nodes)
        self._logistics = normalize.normalize_logistics(stations, trains)
        self._set_state(ConnectionState.CONNECTED)

    async def start(self) -> None:
        """Probe FRM once, then poll in the background until stopped.

        Raises:
            UpstreamUnavailableError: if the initial probe fails (lets the caller
                fall back to the simulated providers).
        """
        self._set_state(ConnectionState.CONNECTING)
        await self.poll_once()  # initial fetch; raises if FRM is unreachable
        self._task = asyncio.create_task(self._run(), name="frm:poll")

    async def _run(self) -> None:
        interval = self._settings.frm_poll_interval_seconds
        while True:
            await asyncio.sleep(interval)
            try:
                await self.poll_once()
            except asyncio.CancelledError:
                raise
            except UpstreamUnavailableError:
                self._set_state(ConnectionState.ERROR)
                logger.warning("FRM poll failed; retaining last snapshot")

    async def stop(self) -> None:
        """Stop polling and close the HTTP client."""
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        await self._client.aclose()
        self._set_state(ConnectionState.DISCONNECTED)

    def dashboard_snapshot(self) -> DashboardSnapshot:
        """Latest normalized dashboard snapshot (503 until first poll)."""
        if self._dashboard is None:
            raise UpstreamUnavailableError("No FRM dashboard snapshot available yet")
        return self._dashboard

    def world_snapshot(self) -> WorldSnapshot:
        """Latest normalized world snapshot (503 until first poll)."""
        if self._world is None:
            raise UpstreamUnavailableError("No FRM world snapshot available yet")
        return self._world

    def logistics_snapshot(self) -> LogisticsSnapshot:
        """Latest normalized logistics snapshot (503 until first poll)."""
        if self._logistics is None:
            raise UpstreamUnavailableError("No FRM logistics snapshot available yet")
        return self._logistics
