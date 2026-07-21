"""Build the full in-game item catalogue from Satisfactory's community Docs.json.

Every giveable item in the game is an ``FGItemDescriptor`` subclass in the game's
shipped ``CommunityResources/Docs/<locale>.json`` (a UTF-16 file). This script
extracts all of them — parts, resources, equipment, biomass, ammo, consumables,
fuels — into ``database/data/item_catalog.json`` keyed by the game class name
(``Desc_IronPlate_C``), which is what the SpiffCoBridge spawn action resolves.

This is intentionally separate from ``items.json`` (the production planner's
friendly-id seed): the spawn catalogue needs the real ``Desc_*_C`` class name and
must cover the whole game, not just the planner's parts.

Usage:
    python scripts/build_item_catalog.py [path-to-Docs.json]

If no path is given, common Steam install locations are probed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Item-descriptor native classes to harvest. FGItemDescriptor is the generic base
# (parts + fluids); the rest are specialised inventory items.
_ITEM_NATIVE_CLASSES = {
    "FGItemDescriptor",
    "FGResourceDescriptor",
    "FGItemDescriptorBiomass",
    "FGItemDescriptorNuclearFuel",
    "FGItemDescriptorPowerBoosterFuel",
    "FGConsumableDescriptor",
    "FGEquipmentDescriptor",
    "FGPowerShardDescriptor",
    "FGAmmoTypeProjectile",
    "FGAmmoTypeSpreadshot",
    "FGAmmoTypeInstantHit",
}

# Category labels shown/grouped in the picker, by native class.
_CATEGORY_BY_CLASS = {
    "FGResourceDescriptor": "Resource",
    "FGItemDescriptorBiomass": "Biomass",
    "FGItemDescriptorNuclearFuel": "Nuclear Fuel",
    "FGItemDescriptorPowerBoosterFuel": "Power Booster",
    "FGConsumableDescriptor": "Consumable",
    "FGEquipmentDescriptor": "Equipment",
    "FGPowerShardDescriptor": "Power Shard",
    "FGAmmoTypeProjectile": "Ammunition",
    "FGAmmoTypeSpreadshot": "Ammunition",
    "FGAmmoTypeInstantHit": "Ammunition",
    "FGItemDescriptor": "Part",
}

_STACK_SIZE = {
    "SS_ONE": 1,
    "SS_SMALL": 50,
    "SS_MEDIUM": 100,
    "SS_BIG": 200,
    "SS_HUGE": 500,
    "SS_FLUID": 50000,
}

_FORM = {"RF_SOLID": "solid", "RF_LIQUID": "liquid", "RF_GAS": "gas"}

_DEFAULT_DOCS_PATHS = [
    r"K:\SteamLibrary\steamapps\common\Satisfactory\CommunityResources\Docs\en-US.json",
    r"C:\Program Files (x86)\Steam\steamapps\common\Satisfactory\CommunityResources\Docs\en-US.json",
    r"E:\SteamLibrary\steamapps\common\Satisfactory\CommunityResources\Docs\en-US.json",
]

_OUT_PATH = Path(__file__).resolve().parent.parent / "database" / "data" / "item_catalog.json"


def _short(native_class: str) -> str:
    """`/Script/CoreUObject.Class'/Script/FactoryGame.FGItemDescriptor'` -> tail name."""
    return native_class.split(".")[-1].strip("'\"")


def _load_docs(path: Path) -> list[dict]:
    """Read Docs.json, which is UTF-16 (with a couple of encoding fallbacks)."""
    raw = path.read_bytes()
    for encoding in ("utf-16", "utf-16-le", "utf-8-sig", "utf-8"):
        try:
            return json.loads(raw.decode(encoding))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
    raise SystemExit(f"Could not decode {path} as JSON in any known encoding")


def _to_int(raw: object, default: int = 0) -> int:
    try:
        return int(float(str(raw)))
    except (TypeError, ValueError):
        return default


def build(docs_path: Path) -> list[dict]:
    """Return the sorted list of item-catalogue rows extracted from Docs.json."""
    data = _load_docs(docs_path)
    seen: set[str] = set()
    rows: list[dict] = []
    for group in data:
        native = _short(group.get("NativeClass", ""))
        if native not in _ITEM_NATIVE_CLASSES:
            continue
        for cls in group.get("Classes", []):
            class_name = cls.get("ClassName", "")
            name = (cls.get("mDisplayName") or "").strip()
            if not class_name or not name or class_name in seen:
                continue
            seen.add(class_name)
            form = _FORM.get(cls.get("mForm", "RF_SOLID"), "solid")
            category = "Fluid" if form != "solid" else _CATEGORY_BY_CLASS.get(native, "Part")
            rows.append({
                "class_name": class_name,
                "name": name,
                "category": category,
                "form": form,
                "stack_size": _STACK_SIZE.get(cls.get("mStackSize", "SS_ONE"), 0),
                "sink_points": _to_int(cls.get("mResourceSinkPoints")),
            })
    rows.sort(key=lambda r: (r["category"], r["name"].lower()))
    return rows


def main() -> None:
    if len(sys.argv) > 1:
        docs_path = Path(sys.argv[1])
    else:
        docs_path = next((Path(p) for p in _DEFAULT_DOCS_PATHS if Path(p).exists()), None)
        if docs_path is None:
            raise SystemExit(
                "Docs.json not found in default locations; pass its path as an argument.\n"
                "It ships at <Satisfactory>/CommunityResources/Docs/en-US.json"
            )
    rows = build(docs_path)
    payload = {
        "$note": "Full in-game item catalogue for the admin spawn picker. "
                 "Generated by scripts/build_item_catalog.py from the game's Docs.json. "
                 "Keyed by game class_name (Desc_*_C) — do not hand-edit.",
        "source": docs_path.name,
        "count": len(rows),
        "items": rows,
    }
    _OUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    by_cat: dict[str, int] = {}
    for r in rows:
        by_cat[r["category"]] = by_cat.get(r["category"], 0) + 1
    print(f"Wrote {len(rows)} items to {_OUT_PATH}")
    for cat, n in sorted(by_cat.items()):
        print(f"  {cat}: {n}")


if __name__ == "__main__":
    main()
