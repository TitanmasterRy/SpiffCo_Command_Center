"""Static recipe/item game-data access for the production planner.

Loads ``recipes.json``, ``alternate_recipes.json``, and ``items.json`` once
(``lru_cache``) and exposes lookups: recipe by id, the default and all recipes
producing an item, and item metadata. Raw resources are items that no recipe
produces — the leaves of any production tree.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.errors import NotFoundError
from app.schemas.production import ItemInfo, ItemRate, RecipeInfo

_DATA_DIR = Path(__file__).resolve().parents[3] / "database" / "data"
_RECIPES_FILE = _DATA_DIR / "recipes.json"
_ALT_RECIPES_FILE = _DATA_DIR / "alternate_recipes.json"
_ITEMS_FILE = _DATA_DIR / "items.json"


def _parse_recipe(raw: dict[str, Any], *, is_alternate: bool) -> RecipeInfo:
    return RecipeInfo(
        id=raw["id"],
        name=raw["name"],
        machine=raw["machine"],
        duration_seconds=float(raw["duration_seconds"]),
        inputs=[ItemRate(**i) for i in raw["inputs"]],
        outputs=[ItemRate(**o) for o in raw["outputs"]],
        is_alternate=is_alternate,
        unlock=raw.get("unlock"),
    )


@lru_cache(maxsize=1)
def load_recipes() -> tuple[RecipeInfo, ...]:
    """All recipes (base first, then alternates) in file order."""
    base = json.loads(_RECIPES_FILE.read_text(encoding="utf-8"))["recipes"]
    recipes = [_parse_recipe(r, is_alternate=False) for r in base]
    try:
        alt = json.loads(_ALT_RECIPES_FILE.read_text(encoding="utf-8"))["recipes"]
        recipes.extend(_parse_recipe(r, is_alternate=True) for r in alt)
    except OSError:
        pass
    return tuple(recipes)


@lru_cache(maxsize=1)
def load_items() -> tuple[ItemInfo, ...]:
    """All known items in file order."""
    data = json.loads(_ITEMS_FILE.read_text(encoding="utf-8"))
    return tuple(ItemInfo(**i) for i in data["items"])


@lru_cache(maxsize=1)
def items_by_id() -> dict[str, ItemInfo]:
    """Lookup map from item id to :class:`ItemInfo`."""
    return {i.id: i for i in load_items()}


@lru_cache(maxsize=1)
def recipes_by_id() -> dict[str, RecipeInfo]:
    """Lookup map from recipe id to :class:`RecipeInfo`."""
    return {r.id: r for r in load_recipes()}


@lru_cache(maxsize=1)
def _producers() -> dict[str, list[RecipeInfo]]:
    """item id -> recipes producing it (base recipes before alternates)."""
    index: dict[str, list[RecipeInfo]] = {}
    for recipe in load_recipes():
        for out in recipe.outputs:
            index.setdefault(out.item, []).append(recipe)
    return index


def recipes_producing(item_id: str) -> list[RecipeInfo]:
    """All recipes whose outputs include ``item_id`` (may be empty)."""
    return _producers().get(item_id, [])


def default_recipe(item_id: str) -> RecipeInfo | None:
    """The default (first non-alternate, else first) recipe for an item."""
    options = recipes_producing(item_id)
    if not options:
        return None
    for recipe in options:
        if not recipe.is_alternate:
            return recipe
    return options[0]


def get_recipe(recipe_id: str) -> RecipeInfo:
    """Return a recipe by id or raise :class:`NotFoundError`."""
    recipe = recipes_by_id().get(recipe_id)
    if recipe is None:
        raise NotFoundError(f"unknown recipe {recipe_id!r}")
    return recipe


def item_name(item_id: str) -> str:
    """Human name for an item id, falling back to the id itself."""
    info = items_by_id().get(item_id)
    return info.name if info else item_id


def output_rate(recipe: RecipeInfo, item_id: str) -> float:
    """The per-minute output rate of ``item_id`` for ``recipe`` (0 if absent)."""
    return next((o.rate for o in recipe.outputs if o.item == item_id), 0.0)
