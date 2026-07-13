"""Blueprint library endpoints: CRUD, filtering, stats, and import/export."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.blueprints import service as blueprint_service
from app.schemas.blueprint import (
    Blueprint,
    BlueprintExport,
    BlueprintIn,
    BlueprintStats,
    BlueprintSummary,
    BlueprintUpdate,
)

router = APIRouter(prefix="/blueprints", tags=["blueprints"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("", response_model=list[BlueprintSummary])
async def list_blueprints(
    session: SessionDep,
    category: str | None = None,
    tag: str | None = None,
    favorite: bool | None = None,
    q: Annotated[str | None, Query(description="Name/description search")] = None,
) -> list[BlueprintSummary]:
    """Blueprints (newest first), filtered by category/tag/favorite/search."""
    return await blueprint_service.list_blueprints(
        session, category=category, tag=tag, favorite=favorite, query=q
    )


@router.get("/stats", response_model=BlueprintStats)
async def blueprint_stats(session: SessionDep) -> BlueprintStats:
    """Library totals and counts by category and tag."""
    return await blueprint_service.stats(session)


@router.post("", response_model=Blueprint, status_code=status.HTTP_201_CREATED)
async def create_blueprint(body: BlueprintIn, session: SessionDep) -> Blueprint:
    """Create a blueprint."""
    return await blueprint_service.create_blueprint(session, body)


@router.post("/import", response_model=Blueprint, status_code=status.HTTP_201_CREATED)
async def import_blueprint(body: BlueprintExport, session: SessionDep) -> Blueprint:
    """Create a new blueprint from an exported document."""
    return await blueprint_service.import_blueprint(session, body)


@router.get("/{blueprint_id}", response_model=Blueprint)
async def get_blueprint(blueprint_id: int, session: SessionDep) -> Blueprint:
    """Full blueprint with its payload (404 if absent)."""
    return await blueprint_service.get_blueprint(session, blueprint_id)


@router.put("/{blueprint_id}", response_model=Blueprint)
async def update_blueprint(
    blueprint_id: int, body: BlueprintUpdate, session: SessionDep
) -> Blueprint:
    """Partially update a blueprint (including toggling ``favorite``)."""
    return await blueprint_service.update_blueprint(session, blueprint_id, body)


@router.delete("/{blueprint_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_blueprint(blueprint_id: int, session: SessionDep) -> None:
    """Delete a blueprint (404 if absent)."""
    await blueprint_service.delete_blueprint(session, blueprint_id)


@router.get("/{blueprint_id}/export", response_model=BlueprintExport)
async def export_blueprint(blueprint_id: int, session: SessionDep) -> BlueprintExport:
    """Download a blueprint as a portable document (no server ids)."""
    return await blueprint_service.export_blueprint(session, blueprint_id)
