"""Coordinate switching the live data source between the base providers
(simulation or FRM) and a loaded save file.

Holds references to the three services and their base providers so it can swap
every service to save-backed providers on upload and restore them on clear —
keeping the whole app on one coherent source at a time.
"""

from __future__ import annotations

from app.logistics.service import LogisticsProvider, LogisticsService
from app.offline.provider import (
    SaveDataSource,
    SaveGameProvider,
    SaveLogisticsProvider,
    SaveWorldProvider,
)
from app.offline.save_parser import parse_save
from app.schemas.offline import OfflineStatus, SaveSummary
from app.services.game_state import GameStateProvider, GameStateService
from app.world.service import WorldProvider, WorldService

# Source labels for base providers.
BaseSource = str  # "simulation" | "frm"


class OfflineManager:
    """Swaps services between their base providers and a save-backed source."""

    def __init__(
        self,
        *,
        game_state: GameStateService,
        world: WorldService,
        logistics: LogisticsService,
        base_game: GameStateProvider,
        base_world: WorldProvider,
        base_logistics: LogisticsProvider,
        base_source: BaseSource,
    ) -> None:
        self._game_state = game_state
        self._world = world
        self._logistics = logistics
        self._base_game = base_game
        self._base_world = base_world
        self._base_logistics = base_logistics
        self._base_source = base_source
        self._source: SaveDataSource | None = None

    @property
    def active(self) -> bool:
        """True when a save file is the live source."""
        return self._source is not None

    async def load_save(self, data: bytes) -> SaveSummary:
        """Parse *data*, switch every service to it, and refresh once.

        Raises :class:`~app.offline.save_parser.SaveParseError` on bad input.
        """
        source = SaveDataSource(parse_save(data))
        self._game_state.use_provider(SaveGameProvider(source))
        self._world.use_provider(SaveWorldProvider(source))
        self._logistics.use_provider(SaveLogisticsProvider(source))
        self._source = source
        await self._refresh_all()
        return source.summary()

    async def set_base(
        self,
        *,
        game: GameStateProvider,
        world: WorldProvider,
        logistics: LogisticsProvider,
        source: BaseSource,
    ) -> None:
        """Replace the base (non-save) providers, e.g. after FRM reconfiguration.

        When no save is active the new base becomes the live source immediately
        (services are swapped and refreshed once). When a save *is* active only
        the stored base changes, so a later :meth:`clear` restores the new base.
        """
        self._base_game = game
        self._base_world = world
        self._base_logistics = logistics
        self._base_source = source
        if self._source is None:
            self._game_state.use_provider(game)
            self._world.use_provider(world)
            self._logistics.use_provider(logistics)
            await self._refresh_all()

    async def clear(self) -> None:
        """Restore the base providers and refresh (no-op if not active)."""
        if self._source is None:
            return
        self._game_state.use_provider(self._base_game)
        self._world.use_provider(self._base_world)
        self._logistics.use_provider(self._base_logistics)
        self._source = None
        await self._refresh_all()

    def status(self) -> OfflineStatus:
        """Current source and, when a save is loaded, its summary."""
        if self._source is not None:
            return OfflineStatus(active=True, source="save", save=self._source.summary())
        source = "frm" if self._base_source == "frm" else "simulation"
        return OfflineStatus(active=False, source=source, save=None)

    async def _refresh_all(self) -> None:
        await self._game_state.refresh()
        await self._world.refresh()
        await self._logistics.refresh()
