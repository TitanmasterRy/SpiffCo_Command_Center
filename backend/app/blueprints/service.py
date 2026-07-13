"""Blueprint library service: CRUD, filtering, stats, and import/export."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import NotFoundError
from app.models.blueprint import Blueprint as BlueprintRow
from app.schemas.blueprint import (
    Blueprint,
    BlueprintExport,
    BlueprintIn,
    BlueprintStats,
    BlueprintSummary,
    BlueprintUpdate,
)


def _to_summary(row: BlueprintRow) -> BlueprintSummary:
    return BlueprintSummary(
        id=row.id,
        name=row.name,
        description=row.description,
        category=row.category,
        tags=list(row.tags),
        favorite=row.favorite,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _to_schema(row: BlueprintRow) -> Blueprint:
    return Blueprint(**_to_summary(row).model_dump(), data=dict(row.data))


async def _get_row(session: AsyncSession, blueprint_id: int) -> BlueprintRow:
    row = await session.get(BlueprintRow, blueprint_id)
    if row is None:
        raise NotFoundError(f"blueprint {blueprint_id} does not exist")
    return row


async def list_blueprints(
    session: AsyncSession,
    *,
    category: str | None = None,
    tag: str | None = None,
    favorite: bool | None = None,
    query: str | None = None,
) -> list[BlueprintSummary]:
    """Blueprints (newest first) filtered by category/tag/favorite/search."""
    rows = (
        await session.execute(select(BlueprintRow).order_by(BlueprintRow.updated_at.desc()))
    ).scalars().all()
    q = query.strip().lower() if query else None
    result: list[BlueprintSummary] = []
    for row in rows:
        if category is not None and row.category != category:
            continue
        if favorite is not None and row.favorite != favorite:
            continue
        if tag is not None and tag not in row.tags:
            continue
        if q and q not in row.name.lower() and q not in row.description.lower():
            continue
        result.append(_to_summary(row))
    return result


async def get_blueprint(session: AsyncSession, blueprint_id: int) -> Blueprint:
    """A full blueprint with its payload, or 404."""
    return _to_schema(await _get_row(session, blueprint_id))


async def create_blueprint(session: AsyncSession, payload: BlueprintIn) -> Blueprint:
    """Create a blueprint."""
    row = BlueprintRow(
        name=payload.name,
        description=payload.description,
        category=payload.category,
        tags=list(payload.tags),
        favorite=payload.favorite,
        data=dict(payload.data),
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return _to_schema(row)


async def update_blueprint(
    session: AsyncSession, blueprint_id: int, payload: BlueprintUpdate
) -> Blueprint:
    """Apply a partial update to a blueprint."""
    row = await _get_row(session, blueprint_id)
    fields = payload.model_dump(exclude_unset=True)
    for key, value in fields.items():
        setattr(row, key, value)
    await session.commit()
    await session.refresh(row)
    return _to_schema(row)


async def delete_blueprint(session: AsyncSession, blueprint_id: int) -> None:
    """Delete a blueprint or raise 404."""
    row = await _get_row(session, blueprint_id)
    await session.delete(row)
    await session.commit()


async def stats(session: AsyncSession) -> BlueprintStats:
    """Totals and counts by category and tag across the library."""
    rows = (await session.execute(select(BlueprintRow))).scalars().all()
    by_category: dict[str, int] = {}
    by_tag: dict[str, int] = {}
    favorites = 0
    for row in rows:
        by_category[row.category] = by_category.get(row.category, 0) + 1
        if row.favorite:
            favorites += 1
        for tag in row.tags:
            by_tag[tag] = by_tag.get(tag, 0) + 1
    return BlueprintStats(
        total=len(rows), favorites=favorites, by_category=by_category, by_tag=by_tag
    )


async def export_blueprint(session: AsyncSession, blueprint_id: int) -> BlueprintExport:
    """Portable document for one blueprint (no server ids)."""
    row = await _get_row(session, blueprint_id)
    return BlueprintExport(
        name=row.name,
        description=row.description,
        category=row.category,
        tags=list(row.tags),
        data=dict(row.data),
        exported_at=datetime.now(UTC),
    )


async def import_blueprint(session: AsyncSession, doc: BlueprintExport) -> Blueprint:
    """Create a new blueprint from an exported document."""
    return await create_blueprint(
        session,
        BlueprintIn(
            name=doc.name,
            description=doc.description,
            category=doc.category,
            tags=doc.tags,
            data=doc.data,
        ),
    )
