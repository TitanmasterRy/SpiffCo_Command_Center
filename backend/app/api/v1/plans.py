"""Factory-planner endpoints: plan CRUD, versioning, and import/export."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.planner import service as planner_service
from app.schemas.planner import (
    FactoryPlan,
    PlanCreate,
    PlanExport,
    PlanSummaryInfo,
    PlanUpdate,
    PlanVersion,
)

router = APIRouter(prefix="/plans", tags=["planner"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("", response_model=list[PlanSummaryInfo])
async def list_plans(session: SessionDep) -> list[PlanSummaryInfo]:
    """All plans (newest first), without layout bodies."""
    return await planner_service.list_plans(session)


@router.post("", response_model=FactoryPlan, status_code=status.HTTP_201_CREATED)
async def create_plan(body: PlanCreate, session: SessionDep) -> FactoryPlan:
    """Create a plan; rejects invalid layouts with ``validation_failed``."""
    return await planner_service.create_plan(session, body)


@router.post("/import", response_model=FactoryPlan, status_code=status.HTTP_201_CREATED)
async def import_plan(body: PlanExport, session: SessionDep) -> FactoryPlan:
    """Create a new plan from an exported document."""
    return await planner_service.import_plan(session, body)


@router.get("/{plan_id}", response_model=FactoryPlan)
async def get_plan(plan_id: int, session: SessionDep) -> FactoryPlan:
    """Full plan with current layout and derived summary (404 if absent)."""
    return await planner_service.get_plan(session, plan_id)


@router.put("/{plan_id}", response_model=FactoryPlan)
async def update_plan(plan_id: int, body: PlanUpdate, session: SessionDep) -> FactoryPlan:
    """Update metadata and/or layout; a new layout appends a version."""
    return await planner_service.update_plan(session, plan_id, body)


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plan(plan_id: int, session: SessionDep) -> None:
    """Delete a plan and its version history (404 if absent)."""
    await planner_service.delete_plan(session, plan_id)


@router.get("/{plan_id}/versions", response_model=list[PlanVersion])
async def list_versions(plan_id: int, session: SessionDep) -> list[PlanVersion]:
    """Version history for a plan, oldest first."""
    return await planner_service.list_versions(session, plan_id)


@router.post("/{plan_id}/revert/{version}", response_model=FactoryPlan)
async def revert_plan(plan_id: int, version: int, session: SessionDep) -> FactoryPlan:
    """Restore a past version's layout as a new version (non-destructive)."""
    return await planner_service.revert_plan(session, plan_id, version)


@router.get("/{plan_id}/export", response_model=PlanExport)
async def export_plan(plan_id: int, session: SessionDep) -> PlanExport:
    """Download the current layout as a portable document (no server ids)."""
    return await planner_service.export_plan(session, plan_id)
