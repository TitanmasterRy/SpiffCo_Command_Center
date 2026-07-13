"""Schemas for the production planner: recipes, items, and solved plans.

A *plan request* names a target item and desired output rate; the solver
(``app/production/solver.py``) resolves the recipe tree into a
:class:`ProductionNode` hierarchy plus rolled-up totals (power, machine counts,
raw-material and byproduct rates, and a build-cost "shopping list").
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ItemRate(BaseModel):
    """An item flowing at a given rate (items/min)."""

    item: str
    rate: float


class RecipeInfo(BaseModel):
    """A recipe served to the frontend (base or alternate)."""

    id: str
    name: str
    machine: str
    duration_seconds: float
    inputs: list[ItemRate]
    outputs: list[ItemRate]
    is_alternate: bool = False
    unlock: str | None = None


class ItemInfo(BaseModel):
    """A game item record."""

    id: str
    name: str
    category: str
    stack_size: int
    is_fluid: bool
    sink_points: int


class ProductionRequest(BaseModel):
    """A request to plan production of ``item`` at ``rate_per_min``.

    ``recipe_overrides`` maps an item id to the recipe id to use for it (e.g. an
    alternate); items without an override use their default recipe.
    ``somersloop_items`` doubles output (halving machines) for the listed items,
    at a super-linear power cost.
    """

    item: str = Field(min_length=1)
    rate_per_min: float = Field(gt=0, le=1_000_000)
    recipe_overrides: dict[str, str] = Field(default_factory=dict)
    somersloop_items: list[str] = Field(default_factory=list)


class ProductionNode(BaseModel):
    """One step in the resolved production tree."""

    item: str
    item_name: str
    rate_per_min: float = Field(description="Required output of this item at this node")
    is_raw: bool = Field(default=False, description="Raw resource — extracted, not crafted")
    recipe_id: str | None = None
    recipe_name: str | None = None
    machine: str | None = Field(default=None, description="Building id running the recipe")
    machine_name: str | None = None
    machine_count: float = Field(default=0, description="Fractional machines at 100% clock")
    power_mw: float = Field(default=0, description="Power draw for this node's machines")
    somersloop: bool = False
    byproducts: list[ItemRate] = Field(default_factory=list)
    inputs: list[ProductionNode] = Field(default_factory=list)


class ProductionTotals(BaseModel):
    """Rolled-up totals across the whole tree."""

    power_mw: float
    machine_counts: dict[str, float] = Field(description="building id -> fractional machine count")
    raw_materials: dict[str, float] = Field(description="raw item id -> items/min")
    byproducts: dict[str, float] = Field(description="surplus item id -> items/min")
    build_cost: dict[str, int] = Field(description="item id -> qty (ceil machines)")


class ProductionPlan(BaseModel):
    """The full solved plan: the tree plus totals and any warnings."""

    target: ItemRate
    root: ProductionNode
    totals: ProductionTotals
    warnings: list[str] = Field(default_factory=list)
