"""World service: live world snapshot and custom-marker persistence."""

from __future__ import annotations

from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import NotFoundError, UpstreamUnavailableError
from app.models.map_marker import MapMarker
from app.schemas.world import CustomMarker, CustomMarkerIn, Position, WorldSnapshot
from app.services.event_bus import EventBus


class WorldProvider(Protocol):
    """Anything that can produce a normalized world snapshot."""

    def snapshot(self) -> WorldSnapshot: ...


class WorldService:
    """Refreshes world state and publishes it on ``world.*`` topics.

    ``world.players`` streams player positions on every refresh; ``world.features``
    streams the full feature list, but only when feature state actually changed
    (e.g. an artifact was collected or a miner was installed), so the map stays
    live without re-sending a static world every tick.
    """

    def __init__(self, provider: WorldProvider, bus: EventBus) -> None:
        self._provider = provider
        self._bus = bus
        self._latest: WorldSnapshot | None = None

    def use_provider(self, provider: WorldProvider) -> None:
        """Swap the data source (e.g. simulation/FRM ⇄ save file) at runtime."""
        self._provider = provider

    @property
    def latest(self) -> WorldSnapshot:
        """Most recent world snapshot; 503 until the first refresh."""
        if self._latest is None:
            raise UpstreamUnavailableError("No world state available yet")
        return self._latest

    async def refresh(self) -> WorldSnapshot:
        """Pull a fresh snapshot and publish player and feature updates."""
        previous = self._latest
        self._latest = self._provider.snapshot()
        self._bus.publish(
            "world.players", [p.model_dump(mode="json") for p in self._latest.players]
        )
        if previous is None or previous.features != self._latest.features:
            self._bus.publish(
                "world.features",
                [f.model_dump(mode="json") for f in self._latest.features],
            )
        for topic, attr in (
            ("world.belts", "belts"),
            ("world.cables", "cables"),
            ("world.pipes", "pipes"),
        ):
            latest = getattr(self._latest, attr)
            if previous is None or getattr(previous, attr) != latest:
                self._bus.publish(topic, [b.model_dump(mode="json") for b in latest])
        return self._latest


def _to_schema(row: MapMarker) -> CustomMarker:
    return CustomMarker(
        id=row.id,
        name=row.name,
        icon=row.icon,
        color=row.color,
        position=Position(x=row.x, y=row.y, z=row.z),
        notes=row.notes,
    )


async def list_markers(session: AsyncSession) -> list[CustomMarker]:
    """All custom markers, oldest first."""
    rows = (await session.execute(select(MapMarker).order_by(MapMarker.id))).scalars().all()
    return [_to_schema(r) for r in rows]


async def create_marker(session: AsyncSession, marker: CustomMarkerIn) -> CustomMarker:
    """Persist a new custom marker."""
    row = MapMarker(
        name=marker.name,
        icon=marker.icon,
        color=marker.color,
        x=marker.position.x,
        y=marker.position.y,
        z=marker.position.z,
        notes=marker.notes,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return _to_schema(row)


async def delete_marker(session: AsyncSession, marker_id: int) -> None:
    """Delete a marker or raise 404."""
    row = await session.get(MapMarker, marker_id)
    if row is None:
        raise NotFoundError(f"marker {marker_id} does not exist")
    await session.delete(row)
    await session.commit()
