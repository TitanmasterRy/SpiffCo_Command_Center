"""Application factory and lifespan management.

Run with::

    uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api.v1 import api_v1_router
from app.api.ws import router as ws_router
from app.config.logging_config import configure_logging
from app.config.settings import Settings, get_settings
from app.connectors.frm import (
    FrmConnector,
    FrmGameProvider,
    FrmLogisticsProvider,
    FrmWorldProvider,
)
from app.database.engine import get_session_factory, init_database, shutdown_database
from app.errors import NotFoundError, UpstreamUnavailableError, register_exception_handlers
from app.logistics.service import LogisticsProvider, LogisticsService
from app.offline import OfflineManager
from app.services.event_bus import EventBus
from app.services.game_state import GameStateProvider, GameStateService
from app.simulation.logistics import SimulatedLogisticsProvider
from app.simulation.provider import SimulatedGameProvider
from app.simulation.world import SimulatedWorldProvider
from app.workers.scheduler import Scheduler
from app.world.service import WorldProvider, WorldService

logger = logging.getLogger(__name__)


def _register_jobs(
    scheduler: Scheduler,
    bus: EventBus,
    game_state: GameStateService,
    world: WorldService,
    logistics: LogisticsService,
) -> None:
    """Register periodic jobs: heartbeat, state/world/logistics refresh, history."""

    async def heartbeat() -> None:
        bus.publish("system.heartbeat", {"alive": True})

    async def refresh_state() -> None:
        await game_state.refresh()

    async def refresh_world() -> None:
        await world.refresh()

    async def refresh_logistics() -> None:
        await logistics.refresh()

    async def sample_history() -> None:
        await game_state.record_history(get_session_factory())

    settings = get_settings()
    interval = settings.frm_poll_interval_seconds
    scheduler.add_job("system.heartbeat", heartbeat, interval_seconds=15.0)
    scheduler.add_job("game_state.refresh", refresh_state, interval_seconds=interval)
    scheduler.add_job("world.refresh", refresh_world, interval_seconds=interval)
    scheduler.add_job("logistics.refresh", refresh_logistics, interval_seconds=interval)
    scheduler.add_job("game_state.history", sample_history, interval_seconds=30.0)


async def _try_start_frm(settings: Settings, bus: EventBus) -> FrmConnector | None:
    """Start the FRM connector if enabled and reachable, else return None.

    A failed probe falls back to the simulated providers so the app always boots.
    """
    if not settings.frm_enabled:
        return None
    connector = FrmConnector(settings, bus)
    try:
        await connector.start()
        return connector
    except UpstreamUnavailableError:
        logger.warning("FRM enabled but unreachable at %s; using simulation", settings.frm_base_url)
        await connector.stop()
        return None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Start/stop shared resources (database, event bus, scheduler)."""
    settings = get_settings()
    configure_logging(settings)

    await init_database(settings)

    bus = EventBus()
    app.state.event_bus = bus

    # Choose the live FRM connector when enabled and reachable, else simulation.
    frm = await _try_start_frm(settings, bus)
    app.state.frm = frm
    game_provider: GameStateProvider
    world_provider: WorldProvider
    logistics_provider: LogisticsProvider
    if frm is not None:
        game_provider = FrmGameProvider(frm)
        world_provider = FrmWorldProvider(frm)
        logistics_provider = FrmLogisticsProvider(frm)
        logger.info("Using FRM providers (live game data)")
    else:
        game_provider = SimulatedGameProvider()
        world_provider = SimulatedWorldProvider()
        logistics_provider = SimulatedLogisticsProvider()

    game_state = GameStateService(game_provider, bus)
    app.state.game_state = game_state
    await game_state.refresh()  # snapshot available before first request

    world = WorldService(world_provider, bus)
    app.state.world = world
    await world.refresh()

    logistics = LogisticsService(logistics_provider, bus)
    app.state.logistics = logistics
    await logistics.refresh()

    # Offline mode: lets a save file replace the live source at runtime.
    app.state.offline = OfflineManager(
        game_state=game_state,
        world=world,
        logistics=logistics,
        base_game=game_provider,
        base_world=world_provider,
        base_logistics=logistics_provider,
        base_source="frm" if frm is not None else "simulation",
    )

    scheduler = Scheduler()
    _register_jobs(scheduler, bus, game_state, world, logistics)
    app.state.scheduler = scheduler
    if settings.scheduler_enabled:
        await scheduler.start()
    else:
        logger.info("Scheduler disabled (SPIFFCO_SCHEDULER_ENABLED=false)")

    logger.info("%s v%s started (%s)", settings.app_name, __version__, settings.environment.value)
    try:
        yield
    finally:
        await scheduler.stop()
        if frm is not None:
            await frm.stop()
        await shutdown_database()
        logger.info("Shutdown complete")


def mount_frontend(app: FastAPI, static_dir: str) -> None:
    """Serve a built SPA from *static_dir* on the same origin as the API.

    Hashed build assets are served directly; every other (non-API) path falls
    back to ``index.html`` so client-side routing works on deep links. No-op if
    the directory has no ``index.html`` (the dev setup, where Vite serves it).
    """
    if not static_dir:
        return
    root = Path(static_dir)
    index = root / "index.html"
    if not index.is_file():
        logger.warning("static_dir %s has no index.html; not serving frontend", static_dir)
        return

    assets = root / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str) -> FileResponse:
        """Serve a real static file if present, else the SPA entrypoint."""
        if full_path.startswith(("api/", "ws")):
            raise NotFoundError(f"No route for /{full_path}")
        candidate = root / full_path
        if full_path and candidate.is_file() and candidate.resolve().is_relative_to(root.resolve()):
            return FileResponse(candidate)
        return FileResponse(index)

    logger.info("Serving frontend from %s", static_dir)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the FastAPI application.

    Args:
        settings: Optional settings override (used by tests); defaults to
            environment-derived settings.
    """
    settings = settings or get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(api_v1_router)
    app.include_router(ws_router)
    mount_frontend(app, settings.static_dir)
    return app


app = create_app()
