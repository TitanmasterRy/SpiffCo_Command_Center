"""Tests for the production planner: recipe tree, totals, alternates, API."""

from __future__ import annotations

from httpx import AsyncClient

from app.production.solver import solve
from app.schemas.production import ProductionRequest


def _find(node, item):
    """Depth-first search for the first node producing/representing an item."""
    if node.item == item:
        return node
    for child in node.inputs:
        hit = _find(child, item)
        if hit:
            return hit
    return None


def test_solve_simple_chain_sizes_machines() -> None:
    # Iron Plate: constructor makes 20/min from 30/min iron ingot.
    plan = solve(ProductionRequest(item="iron-plate", rate_per_min=20))
    assert plan.root.machine == "constructor"
    assert plan.root.machine_count == 1.0
    # One smelter feeds 30/min iron ingot from 30/min iron ore (raw).
    ingot = _find(plan.root, "iron-ingot")
    assert ingot is not None and ingot.machine == "smelter"
    ore = _find(plan.root, "iron-ore")
    assert ore is not None and ore.is_raw
    assert plan.totals.raw_materials["iron-ore"] == 30.0


def test_solve_totals_power_and_machines() -> None:
    plan = solve(ProductionRequest(item="iron-plate", rate_per_min=20))
    # constructor 4 MW + smelter 4 MW, one machine each.
    assert plan.totals.machine_counts == {"constructor": 1.0, "smelter": 1.0}
    assert plan.totals.power_mw == 8.0
    # Build cost rolls up ceil(machines) x building cost.
    assert plan.totals.build_cost  # non-empty


def test_reinforced_plate_multi_input() -> None:
    plan = solve(ProductionRequest(item="reinforced-iron-plate", rate_per_min=5))
    # RIP assembler: 30 iron-plate + 60 screw -> 5 RIP. One assembler.
    assert plan.root.machine == "assembler"
    assert plan.root.machine_count == 1.0
    screw = _find(plan.root, "screw")
    assert screw is not None and screw.machine == "constructor"
    assert plan.totals.raw_materials["iron-ore"] > 0


def test_alternate_recipe_override() -> None:
    base = solve(ProductionRequest(item="screw", rate_per_min=40))
    assert base.root.recipe_id == "screw"
    alt = solve(
        ProductionRequest(
            item="screw", rate_per_min=40, recipe_overrides={"screw": "alt-cast-screw"}
        )
    )
    assert alt.root.recipe_id == "alt-cast-screw"
    # Cast screw skips the iron-rod step, consuming iron ingot directly.
    assert _find(alt.root, "iron-rod") is None


def test_somersloop_halves_machines_and_grows_power() -> None:
    plain = solve(ProductionRequest(item="iron-plate", rate_per_min=20))
    sloop = solve(
        ProductionRequest(item="iron-plate", rate_per_min=20, somersloop_items=["iron-plate"])
    )
    plain_root = plain.root
    sloop_root = sloop.root
    assert sloop_root.machine_count == plain_root.machine_count / 2
    assert sloop_root.somersloop is True
    # Same net throughput -> ~2x power for the amplified node.
    assert sloop_root.power_mw == plain_root.power_mw * 2


def test_invalid_override_warns_and_falls_back() -> None:
    plan = solve(
        ProductionRequest(item="screw", rate_per_min=40, recipe_overrides={"screw": "wire"})
    )
    assert plan.root.recipe_id == "screw"  # fell back to default
    assert any("does not produce" in w for w in plan.warnings)


async def test_production_plan_endpoint(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/production/plan", json={"item": "iron-plate", "rate_per_min": 40}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["target"] == {"item": "iron-plate", "rate": 40}
    assert body["totals"]["machine_counts"]["constructor"] == 2.0


async def test_production_unknown_recipe_404(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/production/plan",
        json={"item": "iron-plate", "rate_per_min": 10, "recipe_overrides": {"iron-plate": "nope"}},
    )
    assert resp.status_code == 404


async def test_gamedata_recipes_and_items(client: AsyncClient) -> None:
    recipes = (await client.get("/api/v1/gamedata/recipes")).json()
    assert any(r["is_alternate"] for r in recipes)
    items = (await client.get("/api/v1/gamedata/items")).json()
    assert {i["id"] for i in items} >= {"iron-ore", "iron-plate"}
