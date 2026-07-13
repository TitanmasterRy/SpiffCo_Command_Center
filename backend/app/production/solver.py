"""Production solver: resolve a target item+rate into a full recipe tree.

Given a target, the solver walks recipes depth-first, sizing each step by the
downstream demand, until it reaches raw resources (items no recipe produces).
Machine counts are fractional (a machine at 100% clock); somersloop-amplified
nodes produce double output at a super-linear power cost. Cycles are broken
defensively and reported as warnings rather than looping forever.
"""

from __future__ import annotations

import math

from app.planner.gamedata import buildings_by_id
from app.production.data import (
    default_recipe,
    get_recipe,
    item_name,
    output_rate,
    recipes_producing,
)
from app.schemas.production import (
    ItemRate,
    ProductionNode,
    ProductionPlan,
    ProductionRequest,
    ProductionTotals,
    RecipeInfo,
)

# Somersloop production amplification: double output, but power scales with the
# square of the multiplier (net ~2x power for 2x output on the same footprint).
_SOMERSLOOP_OUTPUT_MULT = 2.0
_SOMERSLOOP_POWER_MULT = _SOMERSLOOP_OUTPUT_MULT**2
_MAX_DEPTH = 40


def _choose_recipe(
    item: str, overrides: dict[str, str], warnings: list[str]
) -> RecipeInfo | None:
    """Pick the recipe for ``item``: an override if valid, else the default."""
    override_id = overrides.get(item)
    if override_id is not None:
        recipe = get_recipe(override_id)
        if output_rate(recipe, item) <= 0:
            warnings.append(f"recipe {override_id!r} does not produce {item!r}; using default")
        else:
            return recipe
    return default_recipe(item)


def _solve(
    item: str,
    rate: float,
    req: ProductionRequest,
    warnings: list[str],
    path: frozenset[str],
    depth: int,
) -> ProductionNode:
    name = item_name(item)

    if depth > _MAX_DEPTH:
        warnings.append(f"max depth reached at {item!r}; treating as raw")
        return ProductionNode(item=item, item_name=name, rate_per_min=rate, is_raw=True)

    if item in path:
        warnings.append(f"recipe cycle detected at {item!r}; treating as raw")
        return ProductionNode(item=item, item_name=name, rate_per_min=rate, is_raw=True)

    recipe = _choose_recipe(item, req.recipe_overrides, warnings)
    if recipe is None:
        # No recipe produces this item -> raw resource leaf.
        if recipes_producing(item):  # pragma: no cover - defensive
            warnings.append(f"no usable recipe for {item!r}")
        return ProductionNode(item=item, item_name=name, rate_per_min=rate, is_raw=True)

    somersloop = item in req.somersloop_items
    per_machine = output_rate(recipe, item) * (_SOMERSLOOP_OUTPUT_MULT if somersloop else 1.0)
    machines = rate / per_machine if per_machine > 0 else 0.0

    building = buildings_by_id().get(recipe.machine)
    if building is None:
        warnings.append(f"unknown machine {recipe.machine!r} for recipe {recipe.id!r}")
    base_power = building.power_mw if building else 0.0
    power = machines * base_power * (_SOMERSLOOP_POWER_MULT if somersloop else 1.0)

    byproducts = [
        ItemRate(item=o.item, rate=round(o.rate * machines, 4))
        for o in recipe.outputs
        if o.item != item
    ]

    child_path = path | {item}
    inputs = [
        _solve(inp.item, inp.rate * machines, req, warnings, child_path, depth + 1)
        for inp in recipe.inputs
    ]

    return ProductionNode(
        item=item,
        item_name=name,
        rate_per_min=round(rate, 4),
        is_raw=False,
        recipe_id=recipe.id,
        recipe_name=recipe.name,
        machine=recipe.machine,
        machine_name=building.name if building else recipe.machine,
        machine_count=round(machines, 4),
        power_mw=round(power, 4),
        somersloop=somersloop,
        byproducts=byproducts,
        inputs=inputs,
    )


def _collect(node: ProductionNode, totals: _Accumulator) -> None:
    if node.is_raw:
        totals.raw[node.item] = totals.raw.get(node.item, 0.0) + node.rate_per_min
        return
    totals.power += node.power_mw
    if node.machine:
        totals.machines[node.machine] = totals.machines.get(node.machine, 0.0) + node.machine_count
    for bp in node.byproducts:
        totals.byproducts[bp.item] = totals.byproducts.get(bp.item, 0.0) + bp.rate
    for child in node.inputs:
        _collect(child, totals)


class _Accumulator:
    """Mutable rollup carried through the tree walk."""

    def __init__(self) -> None:
        self.power = 0.0
        self.machines: dict[str, float] = {}
        self.raw: dict[str, float] = {}
        self.byproducts: dict[str, float] = {}


def _build_cost(machines: dict[str, float]) -> dict[str, int]:
    """Construction shopping list: ceil(machine count) x each building's cost."""
    cost: dict[str, int] = {}
    catalog = buildings_by_id()
    for building_id, count in machines.items():
        building = catalog.get(building_id)
        if building is None:
            continue
        units = math.ceil(count)
        for item, qty in building.build_cost.items():
            cost[item] = cost.get(item, 0) + qty * units
    return cost


def solve(req: ProductionRequest) -> ProductionPlan:
    """Resolve ``req`` into a full production plan with rolled-up totals."""
    warnings: list[str] = []
    root = _solve(req.item, req.rate_per_min, req, warnings, frozenset(), 0)

    acc = _Accumulator()
    _collect(root, acc)
    totals = ProductionTotals(
        power_mw=round(acc.power, 3),
        machine_counts={k: round(v, 4) for k, v in acc.machines.items()},
        raw_materials={k: round(v, 4) for k, v in acc.raw.items()},
        byproducts={k: round(v, 4) for k, v in acc.byproducts.items() if v > 1e-9},
        build_cost=_build_cost(acc.machines),
    )
    return ProductionPlan(
        target=ItemRate(item=req.item, rate=req.rate_per_min),
        root=root,
        totals=totals,
        warnings=warnings,
    )
