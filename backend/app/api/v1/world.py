"""World map endpoints: snapshot and custom-marker CRUD."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.schemas.world import CustomMarker, CustomMarkerIn, WorldSnapshot
from app.world import service as world_service
from app.world.service import WorldService

router = APIRouter(prefix="/world", tags=["world"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def _service(request: Request) -> WorldService:
    service: WorldService = request.app.state.world
    return service


@router.get("", response_model=WorldSnapshot)
async def world_snapshot(request: Request) -> WorldSnapshot:
    """Latest world snapshot: features + live players. Players also stream on
    WS topic ``world.players``."""
    return _service(request).latest


@router.get("/markers", response_model=list[CustomMarker])
async def list_markers(session: SessionDep) -> list[CustomMarker]:
    """All user-created markers."""
    return await world_service.list_markers(session)


@router.post("/markers", response_model=CustomMarker, status_code=status.HTTP_201_CREATED)
async def create_marker(body: CustomMarkerIn, session: SessionDep) -> CustomMarker:
    """Create a custom marker."""
    return await world_service.create_marker(session, body)


@router.delete("/markers/{marker_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_marker(marker_id: int, session: SessionDep) -> None:
    """Delete a custom marker (404 if absent)."""
    await world_service.delete_marker(session, marker_id)
