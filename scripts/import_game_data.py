#!/usr/bin/env python3
"""Import SpiffCo static game data from the game's ``Docs.json``.

Satisfactory ships a machine-readable dump of every item, recipe, and buildable
at::

    <SatisfactoryInstall>/CommunityResources/Docs/Docs.json

This script parses that dump and regenerates the JSON files under
``database/data/`` in the exact shapes the backend loaders expect
(``app.production.data``, ``app.planner.gamedata``, ``app.power.data``,
``app.logistics.data``). Run it once whenever the game updates::

    python scripts/import_game_data.py --docs "C:/.../Docs/Docs.json"
    python scripts/import_game_data.py --docs Docs.json --dry-run

What it (re)generates from ``Docs.json``:

* ``items.json``            — every item/part/resource descriptor
* ``resources.json``        — raw resource descriptors + their extractor
* ``recipes.json``          — automatable machine recipes (base)
* ``alternate_recipes.json``— the "Alternate:" recipes
* ``buildings.json``        — manufacturers + extractors (planner catalog)
* ``build_costs.json``      — construction cost per buildable (build-gun recipes)
* ``machines.json``         — manufacturer clock/power-exponent/somersloop data
* ``power_buildings.json``  — fuel/nuclear/geothermal generators

What it deliberately does NOT touch (no coordinates in ``Docs.json``):

* ``resource_nodes.json`` / ``collectibles.json`` — world *positions* come from
  map extraction, not the docs dump. Those stay under separate map-data tooling.
* ``transportation.json`` — belt/pipe/vehicle capacities are hand-curated tiers.

The output is intentionally byte-shape-compatible with the existing seed files so
nothing downstream (schemas, solver, planner) needs to change — only the data
grows from the seed subset to the full catalog.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# --------------------------------------------------------------------------- #
# Docs.json is a list of ``{"NativeClass": "...", "Classes": [ {...}, ... ]}``.
# We bucket the native classes we care about by a substring of NativeClass.
# --------------------------------------------------------------------------- #

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_OUT = _REPO_ROOT / "database" / "data"

# Stack-size enum (Docs) -> item count.
_STACK_SIZES = {
    "SS_ONE": 1,
    "SS_SMALL": 50,
    "SS_MEDIUM": 100,
    "SS_BIG": 200,
    "SS_HUGE": 500,
    "SS_FLUID": 50,  # fluids are stored in tanks, not stacks; nominal value.
}
_FLUID_FORMS = {"RF_LIQUID", "RF_GAS"}

# Buildings that "produce" build-gun recipes hold the construction cost, not a
# production recipe. Detect them so their recipes route to build_costs.json.
_BUILD_GUN_HINTS = ("BuildGun", "FGBuildGun", "BP_BuildGun")

# Manufacturer native classes whose recipes are automatable production recipes.
_MANUFACTURER_HINTS = (
    "FGBuildableManufacturer",
    "FGBuildableManufacturerVariablePower",
)
_EXTRACTOR_HINTS = (
    "FGBuildableResourceExtractor",
    "FGBuildableWaterPump",
    "FGBuildableFrackingExtractor",
)
_GENERATOR_HINTS = (
    "FGBuildableGeneratorFuel",
    "FGBuildableGeneratorNuclear",
    "FGBuildableGeneratorGeoThermal",
)


def slugify(display: str) -> str:
    """Human display name -> stable kebab-case id (matches the seed files).

    ``"Iron Ore"`` -> ``"iron-ore"``; ``"Alternate: Pure Iron Ingot"`` keeps only
    the meaningful words. Cross-references (recipe item ids, machine ids) are all
    derived through this same function, so the output is internally consistent.
    """
    cleaned = re.sub(r"[^a-z0-9]+", "-", display.strip().lower())
    return cleaned.strip("-") or "unknown"


def class_name_slug(class_name: str) -> str:
    """Fallback id from a ``Desc_IronOre_C`` style class name."""
    core = re.sub(r"_C$", "", class_name)
    core = re.sub(r"^(Desc|Recipe|Build|BP)_", "", core)
    # Split CamelCase into words, then slugify.
    spaced = re.sub(r"(?<!^)(?=[A-Z])", " ", core)
    return slugify(spaced)


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# Docs stores item references as
#   ((ItemClass=.../Desc_Foo.Desc_Foo_C',Amount=1),(...))
# The path may be wrapped in single and/or double quotes depending on game
# version, so tolerate any run of quote characters between the class and Amount.
_ITEM_REF_RE = re.compile(r"\.(\w+)_C['\"]*,\s*Amount=(\d+)")


def parse_item_amounts(blob: str) -> list[tuple[str, int]]:
    """Parse an ``mIngredients`` / ``mProduct`` blob into ``(class, amount)``."""
    return [(m.group(1) + "_C", int(m.group(2))) for m in _ITEM_REF_RE.finditer(blob or "")]


# Docs stores producer/building references as a list of class paths.
_CLASS_PATH_RE = re.compile(r"\.(\w+)_C[\"']?")


def parse_class_list(blob: str) -> list[str]:
    """Parse an ``mProducedIn`` blob into a list of ``Foo_C`` class names."""
    return [m.group(1) + "_C" for m in _CLASS_PATH_RE.finditer(blob or "")]


def load_docs(path: Path) -> list[dict[str, Any]]:
    """Load Docs.json, handling its UTF-16 encoding (with UTF-8 fallback)."""
    for encoding in ("utf-16", "utf-8-sig", "utf-8"):
        try:
            parsed: list[dict[str, Any]] = json.loads(path.read_text(encoding=encoding))
            return parsed
        except (UnicodeError, UnicodeDecodeError):
            continue
        except json.JSONDecodeError:
            continue
    raise SystemExit(f"Could not decode {path} as UTF-16 or UTF-8 JSON")


def bucket_classes(docs: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Index every class list by its ``NativeClass`` string for lookup."""
    out: dict[str, list[dict[str, Any]]] = {}
    for group in docs:
        native = str(group.get("NativeClass", ""))
        out.setdefault(native, []).extend(group.get("Classes", []) or [])
    return out


def _matches(native: str, hints: tuple[str, ...]) -> bool:
    return any(h in native for h in hints)


def collect_by_hint(
    buckets: dict[str, list[dict[str, Any]]], hints: tuple[str, ...]
) -> list[dict[str, Any]]:
    """All class entries whose NativeClass matches any of ``hints``."""
    result: list[dict[str, Any]] = []
    for native, entries in buckets.items():
        if _matches(native, hints):
            result.extend(entries)
    return result


# --------------------------------------------------------------------------- #
# Builders — each returns the list written into one data file.
# --------------------------------------------------------------------------- #


def build_items(
    buckets: dict[str, list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], dict[str, str], set[str]]:
    """Build the item catalog.

    Returns the item records plus two lookup helpers used by later builders:
    ``class -> item id`` and the set of fluid class names.
    """
    items: list[dict[str, Any]] = []
    class_to_id: dict[str, str] = {}
    fluids: set[str] = set()
    seen: set[str] = set()

    descriptors = collect_by_hint(buckets, ("Descriptor",))
    for c in descriptors:
        class_name = str(c.get("ClassName", ""))
        display = str(c.get("mDisplayName", "")) or class_name
        if not class_name or not display:
            continue
        item_id = slugify(display)
        if item_id in seen:  # display-name collision -> disambiguate by class.
            item_id = class_name_slug(class_name)
        seen.add(item_id)
        class_to_id[class_name] = item_id

        form = str(c.get("mForm", "RF_SOLID"))
        is_fluid = form in _FLUID_FORMS
        if is_fluid:
            fluids.add(class_name)
        items.append(
            {
                "id": item_id,
                "name": display,
                "category": _item_category(c),
                "stack_size": _STACK_SIZES.get(str(c.get("mStackSize")), 0),
                "is_fluid": is_fluid,
                "sink_points": int(_num(c.get("mResourceSinkPoints"))),
            }
        )
    return items, class_to_id, fluids


def _item_category(c: dict[str, Any]) -> str:
    """Coarse category bucket used by the frontend filters."""
    form = str(c.get("mForm", "RF_SOLID"))
    if form in _FLUID_FORMS:
        return "fluid"
    if _num(c.get("mResourceSinkPoints")) == 0 and c.get("mEnergyValue") in (None, "0.000000"):
        return "resource"
    return "part"


def build_resources(
    buckets: dict[str, list[dict[str, Any]]], class_to_id: dict[str, str]
) -> list[dict[str, Any]]:
    """Raw resource descriptors and the extractor that mines/pumps them."""
    resources: list[dict[str, Any]] = []
    for c in collect_by_hint(buckets, ("FGResourceDescriptor",)):
        class_name = str(c.get("ClassName", ""))
        display = str(c.get("mDisplayName", "")) or class_name
        item_id = class_to_id.get(class_name, slugify(display))
        is_fluid = str(c.get("mForm", "RF_SOLID")) in _FLUID_FORMS
        resources.append(
            {
                "id": item_id,
                "name": display,
                "extractor": "water-extractor" if is_fluid else "miner",
                "is_fluid": is_fluid,
            }
        )
    return resources


def _recipe_rates(
    refs: list[tuple[str, int]],
    class_to_id: dict[str, str],
    fluids: set[str],
    duration: float,
) -> list[dict[str, Any]]:
    """Convert ``(class, amount)`` pairs into per-minute ``ItemRate`` dicts."""
    rates: list[dict[str, Any]] = []
    per_min = 60.0 / duration if duration > 0 else 0.0
    for class_name, amount in refs:
        qty = amount / 1000.0 if class_name in fluids else float(amount)
        rates.append(
            {
                "item": class_to_id.get(class_name, class_name_slug(class_name)),
                "rate": round(qty * per_min, 4),
            }
        )
    return rates


def build_recipes(
    buckets: dict[str, list[dict[str, Any]]],
    class_to_id: dict[str, str],
    fluids: set[str],
    building_ids: dict[str, str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, dict[str, int]]]:
    """Split every recipe into base / alternate / build-cost buckets.

    Returns ``(base_recipes, alternate_recipes, build_costs)`` where build_costs
    maps a buildable id to its ``{item_id: qty}`` construction cost.
    """
    base: list[dict[str, Any]] = []
    alternates: list[dict[str, Any]] = []
    build_costs: dict[str, dict[str, int]] = {}

    for c in collect_by_hint(buckets, ("FGRecipe",)):
        class_name = str(c.get("ClassName", ""))
        display = str(c.get("mDisplayName", "")) or class_name
        produced_in = parse_class_list(str(c.get("mProducedIn", "")))
        ingredients = parse_item_amounts(str(c.get("mIngredients", "")))
        products = parse_item_amounts(str(c.get("mProduct", "")))

        # Build-gun recipe -> this is a buildable's construction cost.
        if any(_matches(p, _BUILD_GUN_HINTS) for p in produced_in):
            for prod_class, _amt in products:
                b_id = building_ids.get(prod_class, class_to_id.get(prod_class))
                if b_id:
                    build_costs[b_id] = {
                        class_to_id.get(cls, class_name_slug(cls)): amt
                        for cls, amt in ingredients
                    }
            continue

        # Keep only recipes automatable in a manufacturer we imported.
        machine_class = next((p for p in produced_in if p in building_ids), None)
        if machine_class is None:
            continue

        duration = _num(c.get("mManufactoringDuration"), 1.0)
        recipe = {
            "id": slugify(display),
            "name": display,
            "machine": building_ids[machine_class],
            "duration_seconds": duration,
            "inputs": _recipe_rates(ingredients, class_to_id, fluids, duration),
            "outputs": _recipe_rates(products, class_to_id, fluids, duration),
        }
        is_alt = class_name.startswith("Recipe_Alternate") or display.startswith("Alternate:")
        (alternates if is_alt else base).append(recipe)

    return base, alternates, build_costs


def build_buildings(
    buckets: dict[str, list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, str]]:
    """Manufacturers + extractors -> planner catalog and machine tuning.

    Returns ``(buildings, machines, class_to_building_id)``. Footprints are not
    present in Docs.json, so a nominal default is emitted and flagged; refine
    later from a hand-curated footprint table if precise grids matter.
    """
    buildings: list[dict[str, Any]] = []
    machines: list[dict[str, Any]] = []
    class_to_id: dict[str, str] = {}

    manufacturers = collect_by_hint(buckets, _MANUFACTURER_HINTS)
    extractors = collect_by_hint(buckets, _EXTRACTOR_HINTS)

    for c in manufacturers:
        class_name = str(c.get("ClassName", ""))
        display = str(c.get("mDisplayName", "")) or class_name
        b_id = slugify(display)
        class_to_id[class_name] = b_id
        power = _num(c.get("mPowerConsumption"))
        buildings.append(
            {
                "id": b_id,
                "name": display,
                "category": "production",
                "power_mw": round(power, 3),
                "inputs": 0,  # refined below from the building's recipes
                "outputs": 0,
                "footprint": {"width": 8, "length": 8},  # nominal; not in Docs.json
            }
        )
        machines.append(
            {
                "id": b_id,
                "building": b_id,
                "min_clock": 0.01,
                "max_clock": 2.5,
                "power_exponent": round(_num(c.get("mPowerConsumptionExponent"), 1.321928), 6),
                "somersloop_slots": int(_num(c.get("mProductionShardSlotSize"), 0)),
            }
        )

    for c in extractors:
        class_name = str(c.get("ClassName", ""))
        display = str(c.get("mDisplayName", "")) or class_name
        b_id = slugify(display)
        class_to_id[class_name] = b_id
        buildings.append(
            {
                "id": b_id,
                "name": display,
                "category": "extraction",
                "power_mw": round(_num(c.get("mPowerConsumption")), 3),
                "inputs": 0,
                "outputs": 1,
                "footprint": {"width": 6, "length": 10},
            }
        )
    return buildings, machines, class_to_id


def refine_io_counts(
    buildings: list[dict[str, Any]], base: list[dict[str, Any]], alt: list[dict[str, Any]]
) -> None:
    """Set each building's input/output pin count to its widest recipe."""
    by_id = {b["id"]: b for b in buildings}
    for recipe in (*base, *alt):
        b = by_id.get(recipe["machine"])
        if b is None:
            continue
        b["inputs"] = max(b["inputs"], len(recipe["inputs"]))
        b["outputs"] = max(b["outputs"], len(recipe["outputs"]))


def build_generators(
    buckets: dict[str, list[dict[str, Any]]], class_to_id: dict[str, str]
) -> list[dict[str, Any]]:
    """Fuel / nuclear / geothermal generators for power_buildings.json."""
    generators: list[dict[str, Any]] = []
    for c in collect_by_hint(buckets, _GENERATOR_HINTS):
        display = str(c.get("mDisplayName", "")) or str(c.get("ClassName", ""))
        power = _num(c.get("mPowerProduction"))
        fuels = parse_class_list(str(c.get("mDefaultFuelClasses", "")))
        fuel_id = class_to_id.get(fuels[0]) if fuels else None
        generators.append(
            {
                "id": slugify(display),
                "name": display,
                "power_mw": round(power, 3),
                "fuel": fuel_id or "unknown",
                "fuel_rate": 0.0,  # derived from fuel energy value; refine if needed
                "requires_water": bool(_num(c.get("mRequiresSupplyLineForFuel"))),
            }
        )
    return generators


# --------------------------------------------------------------------------- #


def write_json(path: Path, key: str, records: list[dict[str, Any]], *, dry_run: bool) -> None:
    """Write ``{key: records}`` to ``path`` (or report under ``--dry-run``)."""
    print(f"  {path.name:26} {key}={len(records)}")
    if dry_run:
        return
    path.write_text(json.dumps({key: records}, indent=2) + "\n", encoding="utf-8")


def run(docs_path: Path, out_dir: Path, *, dry_run: bool) -> None:
    """Parse ``docs_path`` and (re)write every data file under ``out_dir``."""
    print(f"Reading {docs_path} ...")
    buckets = bucket_classes(load_docs(docs_path))

    items, class_to_id, fluids = build_items(buckets)
    buildings, machines, building_ids = build_buildings(buckets)
    base, alternates, build_costs = build_recipes(buckets, class_to_id, fluids, building_ids)
    refine_io_counts(buildings, base, alternates)
    resources = build_resources(buckets, class_to_id)
    generators = build_generators(buckets, class_to_id)

    if not items or not base:
        raise SystemExit("Parsed no items/recipes — is this a real Docs.json?")

    print(f"Writing to {out_dir}{' (dry-run)' if dry_run else ''}:")
    write_json(out_dir / "items.json", "items", items, dry_run=dry_run)
    write_json(out_dir / "resources.json", "resources", resources, dry_run=dry_run)
    write_json(out_dir / "recipes.json", "recipes", base, dry_run=dry_run)
    write_json(out_dir / "alternate_recipes.json", "recipes", alternates, dry_run=dry_run)
    write_json(out_dir / "buildings.json", "buildings", buildings, dry_run=dry_run)
    write_json(out_dir / "machines.json", "machines", machines, dry_run=dry_run)
    write_json(out_dir / "power_buildings.json", "power_buildings", generators, dry_run=dry_run)

    cost_records = [{"building": b, "cost": cost} for b, cost in sorted(build_costs.items())]
    write_json(out_dir / "build_costs.json", "build_costs", cost_records, dry_run=dry_run)
    print("Done. (resource_nodes.json / collectibles.json / transportation.json left untouched)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import SpiffCo game data from Docs.json")
    parser.add_argument(
        "--docs", required=True, type=Path, help="Path to the game's Docs.json"
    )
    parser.add_argument(
        "--out", type=Path, default=_DEFAULT_OUT, help=f"Output dir (default: {_DEFAULT_OUT})"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Parse and report counts without writing"
    )
    args = parser.parse_args(argv)

    if not args.docs.is_file():
        parser.error(f"Docs.json not found: {args.docs}")
    args.out.mkdir(parents=True, exist_ok=True)
    run(args.docs, args.out, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
