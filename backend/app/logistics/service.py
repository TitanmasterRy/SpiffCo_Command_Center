"""Logistics service: latest network snapshot and live-train publishing."""

from __future__ import annotations

from typing import Protocol

from app.errors import UpstreamUnavailableError
from app.schemas.logistics import LogisticsSnapshot
from app.services.event_bus import EventBus


class LogisticsProvider(Protocol):
    """Anything that can produce a normalized logistics snapshot."""

    def snapshot(self) -> LogisticsSnapshot: ...


class LogisticsService:
    """Refreshes the network and publishes train positions on ``logistics.trains``."""

    def __init__(self, provider: LogisticsProvider, bus: EventBus) -> None:
        self._provider = provider
        self._bus = bus
        self._latest: LogisticsSnapshot | None = None

    def use_provider(self, provider: LogisticsProvider) -> None:
        """Swap the data source (e.g. simulation/FRM ⇄ save file) at runtime."""
        self._provider = provider

    @property
    def latest(self) -> LogisticsSnapshot:
        """Most recent snapshot; 503 until the first refresh."""
        if self._latest is None:
            raise UpstreamUnavailableError("No logistics state available yet")
        return self._latest

    async def refresh(self) -> LogisticsSnapshot:
        """Pull a fresh snapshot and publish live train positions."""
        self._latest = self._provider.snapshot()
        self._bus.publish(
            "logistics.trains", [t.model_dump(mode="json") for t in self._latest.trains]
        )
        return self._latest
