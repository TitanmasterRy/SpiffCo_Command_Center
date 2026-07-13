"""Runtime FRM configuration: enable/disable and re-point the FRM connection
from the UI without restarting the process.

The FRM connection is normally fixed at startup from environment variables. This
service persists a user override in the ``app_settings`` table and, on change,
tears down the running connector, starts a new one against the new endpoint (or
falls back to simulation if unreachable), and swaps every service's *base*
provider through the :class:`~app.offline.manager.OfflineManager` — so an active
save upload keeps precedence and is restored to the new base on clear.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

from app.config.settings import Settings
from app.connectors.frm import (
    ConnectionState,
    FrmConnector,
    FrmGameProvider,
    FrmLogisticsProvider,
    FrmWorldProvider,
)
from app.connectors.frm.client import FrmClient
from app.database.engine import get_session_factory
from app.errors import NotFoundError, UpstreamUnavailableError
from app.logistics.service import LogisticsProvider
from app.offline.manager import OfflineManager
from app.schemas.system import (
    FrmConfig,
    FrmConfigStatus,
    FrmTestResult,
    SettingValue,
)
from app.services import system_service
from app.services.event_bus import EventBus
from app.services.game_state import GameStateProvider
from app.simulation.logistics import SimulatedLogisticsProvider
from app.simulation.provider import SimulatedGameProvider
from app.simulation.world import SimulatedWorldProvider
from app.world.service import WorldProvider

logger = logging.getLogger(__name__)

#: ``app_settings`` key under which the FRM override is persisted.
SETTING_KEY = "frm.config"


async def load_persisted_config(base_settings: Settings) -> FrmConfig:
    """Load the persisted FRM override, or the env-var defaults if none exists."""
    default = FrmConfig(enabled=base_settings.frm_enabled, base_url=base_settings.frm_base_url)
    async with get_session_factory()() as session:
        try:
            stored = await system_service.get_setting(session, SETTING_KEY)
        except NotFoundError:
            return default
    if not isinstance(stored.value, dict):
        return default
    try:
        return FrmConfig.model_validate(stored.value)
    except ValueError:
        logger.warning("Ignoring malformed persisted FRM config; using defaults")
        return default


class FrmConfigService:
    """Applies FRM configuration changes at runtime and reports live status."""

    def __init__(
        self,
        *,
        base_settings: Settings,
        bus: EventBus,
        offline: OfflineManager,
        config: FrmConfig,
        connector: FrmConnector | None,
        on_connector_change: Callable[[FrmConnector | None], None],
    ) -> None:
        self._base_settings = base_settings
        self._bus = bus
        self._offline = offline
        self._config = config
        self._connector = connector
        self._on_connector_change = on_connector_change
        self._message: str | None = None
        self._lock = asyncio.Lock()

    @property
    def connector(self) -> FrmConnector | None:
        """The active FRM connector, or ``None`` when running on simulation."""
        return self._connector

    def _effective_settings(self, config: FrmConfig) -> Settings:
        return self._base_settings.model_copy(
            update={"frm_enabled": config.enabled, "frm_base_url": config.base_url}
        )

    def status(self) -> FrmConfigStatus:
        """Report the stored config plus the live connection/data-source state."""
        connector = self._connector
        state = connector.state if connector is not None else ConnectionState.DISCONNECTED
        connected = connector is not None and connector.state == ConnectionState.CONNECTED
        source: str
        if self._offline.active:
            source = "save"
        elif connector is not None:
            source = "frm"
        else:
            source = "simulation"
        return FrmConfigStatus(
            enabled=self._config.enabled,
            base_url=self._config.base_url,
            source=source,
            state=state.value,
            connected=connected,
            message=self._message,
        )

    async def apply(self, config: FrmConfig) -> FrmConfigStatus:
        """Persist *config* and reconfigure the live FRM connection.

        Enabling with an unreachable endpoint is not an error: the config is
        saved and the app falls back to simulation, with the reason reported in
        the returned status ``message``.
        """
        async with self._lock:
            # Tear down any existing connector first.
            if self._connector is not None:
                await self._connector.stop()
                self._connector = None
                self._on_connector_change(None)

            new_connector: FrmConnector | None = None
            message: str | None = None
            if config.enabled:
                candidate = FrmConnector(self._effective_settings(config), self._bus)
                try:
                    await candidate.start()
                    new_connector = candidate
                    message = f"Connected to FRM at {config.base_url}."
                    logger.info("FRM reconfigured: connected to %s", config.base_url)
                except UpstreamUnavailableError as exc:
                    await candidate.stop()
                    message = (
                        f"FRM enabled but unreachable at {config.base_url} "
                        f"({exc}); using simulation."
                    )
                    logger.warning("FRM reconfigure probe failed: %s", exc)
            else:
                message = "FRM disabled; using simulation."

            game: GameStateProvider
            world: WorldProvider
            logistics: LogisticsProvider
            if new_connector is not None:
                game = FrmGameProvider(new_connector)
                world = FrmWorldProvider(new_connector)
                logistics = FrmLogisticsProvider(new_connector)
                source = "frm"
            else:
                game = SimulatedGameProvider()
                world = SimulatedWorldProvider()
                logistics = SimulatedLogisticsProvider()
                source = "simulation"

            self._connector = new_connector
            self._on_connector_change(new_connector)
            await self._offline.set_base(
                game=game, world=world, logistics=logistics, source=source
            )

            self._config = config
            self._message = message
            await self._persist(config)
            return self.status()

    async def test(self, base_url: str) -> FrmTestResult:
        """Probe *base_url* for a live FRM mod without changing any state."""
        client = FrmClient(base_url, timeout=self._base_settings.frm_timeout_seconds)
        try:
            reachable = await client.healthy()
        finally:
            await client.aclose()
        message = (
            f"FRM responded at {base_url}."
            if reachable
            else f"No FRM mod reachable at {base_url}."
        )
        return FrmTestResult(reachable=reachable, base_url=base_url, message=message)

    async def _persist(self, config: FrmConfig) -> None:
        async with get_session_factory()() as session:
            await system_service.put_setting(
                session, SettingValue(key=SETTING_KEY, value=config.model_dump())
            )
