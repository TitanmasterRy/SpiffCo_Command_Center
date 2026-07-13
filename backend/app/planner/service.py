"""Factory-planner service: layout validation, summaries, and plan CRUD.

Business logic only — routers stay thin. Layouts are validated (known building,
in-bounds, non-overlapping, legal clock) before any persistence, and every saved
layout appends a :class:`~app.models.plan.PlanVersion` so plans are revertible.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.errors import NotFoundError, ValidationFailedError
from app.models.plan import FactoryPlan as PlanRow
from app.models.plan import PlanVersion as VersionRow
from app.planner.gamedata import get_building
from app.planner.geometry import placement_rect
from app.schemas.planner import (
    FactoryPlan,
    GridSpec,
    Layout,
    PlanCreate,
    PlanExport,
    PlanSummary,
    PlanSummaryInfo,
    PlanUpdate,
    PlanVersion,
)

# Satisfactory power scales super-linearly with clock: draw = base * clock^1.321928.
POWER_EXPONENT = 1.321928

_EMPTY_LAYOUT = Layout(grid=GridSpec(width=40, length=40, cell_cm=100), placements=[])


def validate_layout(layout: Layout) -> None:
    """Validate a layout or raise :class:`ValidationFailedError`.

    Collects *all* per-placement problems into ``details['placements']`` so the
    editor can highlight every offender at once, not just the first.
    """
    errors: dict[str, list[str]] = {}

    def add(pid: str, message: str) -> None:
        errors.setdefault(pid, []).append(message)

    seen_ids: set[str] = set()
    rects = []
    for placement in layout.placements:
        if placement.id in seen_ids:
            add(placement.id, "duplicate placement id")
        seen_ids.add(placement.id)
        try:
            building = get_building(placement.building)
        except NotFoundError:
            add(placement.id, f"unknown building {placement.building!r}")
            continue
        rect = placement_rect(placement, building.footprint, layout.grid.cell_cm)
        if not rect.within(layout.grid):
            add(placement.id, "placement is outside the grid")
        rects.append((placement, rect))

    for i in range(len(rects)):
        for j in range(i + 1, len(rects)):
            (pa, ra), (pb, rb) = rects[i], rects[j]
            if ra.overlaps(rb):
                add(pa.id, f"overlaps placement {pb.id!r}")
                add(pb.id, f"overlaps placement {pa.id!r}")

    if errors:
        raise ValidationFailedError(
            "layout has invalid placements",
            details={"placements": {pid: sorted(set(msgs)) for pid, msgs in errors.items()}},
        )


def summarize(layout: Layout) -> PlanSummary:
    """Derive power draw, machine counts, and build-cost rollup for a layout.

    Assumes the layout is valid (unknown buildings are skipped defensively).
    """
    total_power = 0.0
    machine_counts: dict[str, int] = {}
    build_cost: dict[str, int] = {}
    for placement in layout.placements:
        try:
            building = get_building(placement.building)
        except NotFoundError:
            continue
        total_power += building.power_mw * (placement.clock**POWER_EXPONENT)
        machine_counts[building.id] = machine_counts.get(building.id, 0) + 1
        for item, qty in building.build_cost.items():
            build_cost[item] = build_cost.get(item, 0) + qty
    return PlanSummary(
        total_power_mw=round(total_power, 3),
        machine_count=sum(machine_counts.values()),
        machine_counts=machine_counts,
        build_cost=build_cost,
    )


def _to_layout(raw: object) -> Layout:
    return Layout.model_validate(raw)


def _to_schema(row: PlanRow) -> FactoryPlan:
    layout = _to_layout(row.layout)
    return FactoryPlan(
        id=row.id,
        name=row.name,
        description=row.description,
        version=row.version,
        created_at=row.created_at,
        updated_at=row.updated_at,
        layout=layout,
        summary=summarize(layout),
    )


async def _get_row(session: AsyncSession, plan_id: int, *, with_versions: bool = False) -> PlanRow:
    stmt = select(PlanRow).where(PlanRow.id == plan_id)
    if with_versions:
        stmt = stmt.options(selectinload(PlanRow.versions))
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise NotFoundError(f"plan {plan_id} does not exist")
    return row


async def list_plans(session: AsyncSession) -> list[PlanSummaryInfo]:
    """All plans, newest first, without layout bodies."""
    rows = (
        await session.execute(select(PlanRow).order_by(PlanRow.updated_at.desc()))
    ).scalars().all()
    return [
        PlanSummaryInfo(
            id=r.id,
            name=r.name,
            description=r.description,
            version=r.version,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in rows
    ]


async def get_plan(session: AsyncSession, plan_id: int) -> FactoryPlan:
    """Full plan with layout and derived summary, or 404."""
    return _to_schema(await _get_row(session, plan_id))


async def create_plan(session: AsyncSession, payload: PlanCreate) -> FactoryPlan:
    """Create a plan (version 1) after validating its layout."""
    layout = payload.layout or _EMPTY_LAYOUT
    validate_layout(layout)
    layout_json = layout.model_dump(mode="json")
    row = PlanRow(
        name=payload.name,
        description=payload.description,
        version=1,
        layout=layout_json,
    )
    row.versions.append(VersionRow(version=1, comment="initial", layout=layout_json))
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return _to_schema(row)


async def update_plan(session: AsyncSession, plan_id: int, payload: PlanUpdate) -> FactoryPlan:
    """Update metadata and/or layout. A new layout appends a version."""
    row = await _get_row(session, plan_id, with_versions=True)
    if payload.name is not None:
        row.name = payload.name
    if payload.description is not None:
        row.description = payload.description
    if payload.layout is not None:
        validate_layout(payload.layout)
        layout_json = payload.layout.model_dump(mode="json")
        row.version += 1
        row.layout = layout_json
        row.versions.append(
            VersionRow(version=row.version, comment=payload.comment, layout=layout_json)
        )
    await session.commit()
    await session.refresh(row)
    return _to_schema(row)


async def delete_plan(session: AsyncSession, plan_id: int) -> None:
    """Delete a plan and its versions, or 404."""
    row = await _get_row(session, plan_id)
    await session.delete(row)
    await session.commit()


async def list_versions(session: AsyncSession, plan_id: int) -> list[PlanVersion]:
    """Version history for a plan, oldest first."""
    row = await _get_row(session, plan_id, with_versions=True)
    return [
        PlanVersion(
            version=v.version,
            comment=v.comment,
            created_at=v.created_at,
            layout=_to_layout(v.layout),
        )
        for v in row.versions
    ]


async def revert_plan(session: AsyncSession, plan_id: int, version: int) -> FactoryPlan:
    """Restore a past version's layout as a new version (non-destructive)."""
    row = await _get_row(session, plan_id, with_versions=True)
    target = next((v for v in row.versions if v.version == version), None)
    if target is None:
        raise NotFoundError(f"plan {plan_id} has no version {version}")
    row.version += 1
    row.layout = target.layout
    row.versions.append(
        VersionRow(
            version=row.version,
            comment=f"revert to v{version}",
            layout=target.layout,
        )
    )
    await session.commit()
    await session.refresh(row)
    return _to_schema(row)


async def export_plan(session: AsyncSession, plan_id: int) -> PlanExport:
    """Portable document for the current layout (no server ids)."""
    row = await _get_row(session, plan_id)
    return PlanExport(
        name=row.name,
        description=row.description,
        layout=_to_layout(row.layout),
        exported_at=datetime.now(UTC),
    )


async def import_plan(session: AsyncSession, doc: PlanExport) -> FactoryPlan:
    """Create a new plan from an exported document."""
    return await create_plan(
        session,
        PlanCreate(name=doc.name, description=doc.description, layout=doc.layout),
    )
