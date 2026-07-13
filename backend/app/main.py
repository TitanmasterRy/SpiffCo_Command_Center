"""Application factory and lifespan management.

Run with::

    uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.v1 import api_v1_router
from app.api.ws import router as ws_router
from app.config.logging_config import configure_logging
from app.config.settings import Settings, get_settings
from app.database.engine import get_session_factory, init_database, shutdown_database
from app.errors import register_exception_handlers
from app.logistics.service import LogisticsService
from app.services.event_bus import EventBus
from app.services.game_state import GameStateService
from app.simulation.logistics import SimulatedLogisticsProvider
from app.simulation.provider import SimulatedGameProvider
from app.simulation.world import SimulatedWorldProvider
from app.workers.scheduler import Scheduler
from app.world.service import WorldService

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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Start/stop shared resources (database, event bus, scheduler)."""
    settings = get_settings()
    configure_logging(settings)

    await init_database(settings)

    bus = EventBus()
    app.state.event_bus = bus

    game_state = GameStateService(SimulatedGameProvider(), bus)
    app.state.game_state = game_state
    await game_state.refresh()  # snapshot available before first request

    world = WorldService(SimulatedWorldProvider(), bus)
    app.state.world = world
    await world.refresh()

    logistics = LogisticsService(SimulatedLogisticsProvider(), bus)
    app.state.logistics = logistics
    await logistics.refresh()

    scheduler = Scheduler()
    _register_jobs(scheduler, bus, game_state, world, logistics)
    app.state.scheduler = scheduler
    await scheduler.start()

    logger.info("%s v%s started (%s)", settings.app_name, __version__, settings.environment.value)
    try:
        yield
    finally:
        await scheduler.stop()
        await shutdown_database()
        logger.info("Shutdown complete")


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
    return app


app = create_app()
