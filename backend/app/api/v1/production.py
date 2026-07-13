"""Production-planner endpoint: solve a target into a recipe tree."""

from __future__ import annotations

from fastapi import APIRouter

from app.production.solver import solve
from app.schemas.production import ProductionPlan, ProductionRequest

router = APIRouter(prefix="/production", tags=["production"])


@router.post("/plan", response_model=ProductionPlan)
async def plan_production(body: ProductionRequest) -> ProductionPlan:
    """Resolve a target item + rate into a full production plan.

    Returns the recipe tree plus totals: power draw, machine counts, raw-material
    demand, byproducts, and a construction shopping list. Unknown recipes raise
    ``not_found``; recipe cycles / missing machines surface as ``warnings``.
    """
    return solve(body)
