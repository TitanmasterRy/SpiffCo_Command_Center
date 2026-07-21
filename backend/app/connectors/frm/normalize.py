"""Normalize raw FRM payloads into internal schemas.

Pure functions (no I/O) so they can be unit-tested against captured/fixture FRM
JSON. They are deliberately defensive — the FRM mod's field set varies by version
and installed mods — using ``.get`` with sensible fallbacks so a missing field
degrades gracefully instead of raising. Raw FRM shapes never leave this package.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

from app.schemas.dashboard import (
    DashboardSnapshot,
    FactoryStatus,
    MachineSummary,
    PowerStats,
    ProductionStat,
    StorageLevel,
)
from app.schemas.logistics import (
    LogisticsNode,
    LogisticsSnapshot,
    TrainInfo,
)
from app.schemas.logistics import (
    LogisticsSummary as LogSummary,
)
from app.schemas.world import (
    BeltPath,
    FeatureType,
    MapFeature,
    PlayerInfo,
    Position,
    WorldSnapshot,
)

Raw = dict[str, Any]


def _num(value: Any, default: float = 0.0) -> float:
    """Coerce a value to float, falling back to *default*."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _location(entry: Raw) -> Position:
    """Read a FRM ``location`` object into a :class:`Position` (cm)."""
    loc = entry.get("location") or entry.get("Location") or {}
    return Position(x=_num(loc.get("x")), y=_num(loc.get("y")), z=_num(loc.get("z")))


def _slug(name: str) -> str:
    """Stable, DOM-safe kebab-case id from a display name or FRM identifier.

    Any run of non-alphanumeric characters (spaces, underscores, dots) becomes a
    single hyphen, so ``"Iron Ore"`` -> ``"iron-ore"`` and an FRM id like
    ``"P_2"`` -> ``"p-2"`` (not ``"p_2"``).
    """
    return "-".join(re.findall(r"[a-z0-9]+", name.lower())) or "unknown"


def normalize_power(circuits: Iterable[Raw]) -> PowerStats:
    """Aggregate FRM power circuits into grid-wide :class:`PowerStats`."""
    produced = consumed = capacity = 0.0
    battery_capacity = battery_stored = 0.0
    fuse = False
    for circuit in circuits:
        produced += _num(circuit.get("PowerProduction"))
        consumed += _num(circuit.get("PowerConsumed"))
        capacity += _num(circuit.get("PowerCapacity"))
        cap_mwh = _num(circuit.get("BatteryCapacity"))
        battery_capacity += cap_mwh
        battery_stored += cap_mwh * _num(circuit.get("BatteryPercent")) / 100.0
        fuse = fuse or bool(circuit.get("FuseTriggered"))
    percent = (battery_stored / battery_capacity) if battery_capacity > 0 else 0.0
    return PowerStats(
        produced_mw=round(produced, 3),
        consumed_mw=round(consumed, 3),
        capacity_mw=round(capacity, 3),
        battery_percent=round(min(1.0, max(0.0, percent)), 4),
        battery_capacity_mwh=round(battery_capacity, 3),
        fuse_triggered=fuse,
    )


def _factory_groups(buildings: Iterable[Raw]) -> tuple[list[FactoryStatus], MachineSummary]:
    """Group FRM production buildings by class name into factory summaries."""
    groups: dict[str, dict[str, float]] = {}
    for b in buildings:
        name = str(b.get("Name") or b.get("building") or "Building")
        g = groups.setdefault(name, {"total": 0, "running": 0, "unpowered": 0, "eff": 0.0})
        g["total"] += 1
        # FRM 1.5.x sends capitalized keys (Productivity, PowerInfo); keep the
        # lowercase fallbacks for older/variant payloads.
        productivity = _num(b.get("Productivity", b.get("productivity")), _num(b.get("ManuSpeed")))
        producing = bool(b.get("IsProducing", productivity > 0))
        power_info = b.get("PowerInfo") or b.get("powerInfo") or {}
        fuse = bool(power_info.get("FuseTriggered"))
        powered = bool(b.get("IsConfigured", True)) and not fuse
        if not powered:
            g["unpowered"] += 1
        elif producing:
            g["running"] += 1
        g["eff"] += productivity / 100.0 if productivity > 1 else productivity

    factories: list[FactoryStatus] = []
    totals = MachineSummary()
    for name, g in groups.items():
        total = int(g["total"])
        running = int(g["running"])
        unpowered = int(g["unpowered"])
        idle = max(0, total - running - unpowered)
        eff = g["eff"] / total if total else 0.0
        status = "ok" if eff >= 0.9 else "warn" if eff >= 0.6 else "error"
        machines = MachineSummary(total=total, running=running, idle=idle, unpowered=unpowered)
        factories.append(
            FactoryStatus(
                id=_slug(name),
                name=name,
                status=status,
                efficiency=min(1.0, eff),
                machines=machines,
            )
        )
        totals = MachineSummary(
            total=totals.total + total,
            running=totals.running + running,
            idle=totals.idle + idle,
            unpowered=totals.unpowered + unpowered,
        )
    return factories, totals


def _production(buildings: Iterable[Raw]) -> list[ProductionStat]:
    """Aggregate current/max output per item across all buildings."""
    current: dict[str, float] = {}
    target: dict[str, float] = {}
    for b in buildings:
        for out in b.get("production", []) or []:
            item = str(out.get("Name") or out.get("item") or "item")
            cur = _num(out.get("CurrentProd"))
            current[item] = current.get(item, 0.0) + cur
            target[item] = target.get(item, 0.0) + _num(out.get("MaxProd"), cur)
    return [
        ProductionStat(
            item=_slug(item),
            name=item,
            current_per_min=round(current[item], 3),
            target_per_min=round(target.get(item, current[item]), 3),
        )
        for item in current
    ]


def _storage(inventory: Iterable[Raw]) -> list[StorageLevel]:
    """Storage levels from a FRM world/storage inventory payload."""
    levels: list[StorageLevel] = []
    for entry in inventory:
        name = str(entry.get("Name") or entry.get("item") or "item")
        levels.append(
            StorageLevel(
                item=_slug(name),
                name=name,
                stored=_num(entry.get("Amount") or entry.get("stored")),
                capacity=_num(entry.get("MaxAmount") or entry.get("capacity"), 0.0),
            )
        )
    return levels


def normalize_dashboard(
    power_raw: Iterable[Raw],
    factory_raw: Iterable[Raw],
    inventory_raw: Iterable[Raw] | None = None,
    *,
    source: str = "frm",
) -> DashboardSnapshot:
    """Build a dashboard snapshot from FRM power/factory/inventory payloads."""
    factory_list = list(factory_raw)
    factories, machines = _factory_groups(factory_list)
    return DashboardSnapshot(
        generated_at=datetime.now(UTC),
        source=source,
        power=normalize_power(power_raw),
        machines=machines,
        factories=factories,
        production=_production(factory_list),
        storage=_storage(inventory_raw or []),
        alerts=[],
    )


_NODE_TYPE_MAP = {
    "factory": "factory",
    "trainstation": "train_station",
    "dronestation": "drone_port",
    "truckstation": "truck_station",
}

# FRM returns geysers and resource-well satellites in the generic resource-node
# feed; reclassify them so the map's Geyser / Resource-well layers work. Geysers
# feed geothermal generators; nitrogen gas and water are only obtained from
# Resource Well Pressurizers, so those satellites are always wells. Crude oil
# exists as both surface nodes and well satellites, so it can't be classified by
# resource name — _node_feature_type checks the payload's fracking markers first.
_NODE_FEATURE_TYPE: dict[str, FeatureType] = {
    "geyser": "geyser",
    "nitrogen-gas": "resource_well",
    "water": "resource_well",
}


def _node_feature_type(node: Raw, resource: str) -> FeatureType:
    """Classify a raw FRM resource-node entry into a map feature type.

    FRM tags well satellites/cores via ``NodeType`` (e.g. ``"Fracking
    Satellite"``) and/or a fracking ``ClassName``; those win over the
    name-based fallback so oil wells don't collapse into oil surface nodes.
    """
    marker = f"{node.get('NodeType') or ''} {node.get('ClassName') or ''}".lower()
    if "fracking" in marker:
        return "resource_well"
    if "geyser" in marker:
        return "geyser"
    return _NODE_FEATURE_TYPE.get(resource, "resource_node")


def _pickup_features(
    entries: Iterable[Raw],
    feature_type: FeatureType,
    *,
    default_name: str,
    collected_key: str | None = None,
) -> list[MapFeature]:
    """Map a FRM pickup endpoint (artifacts / slugs / drop pods) to features.

    Endpoints only return items still present in the world, so uncollected is
    the default; *collected_key* (e.g. ``Looted`` for drop pods) overrides that
    when the payload tracks a looted/opened flag.
    """
    features: list[MapFeature] = []
    for i, e in enumerate(entries):
        name = str(e.get("Name") or default_name)
        collected = bool(e.get(collected_key)) if collected_key else False
        meta: dict[str, str | float | int] = {"kind": _slug(name)}
        required = (e.get("RequiredItem") or {}).get("Name")
        if required:
            meta["requires"] = str(required)
        features.append(
            MapFeature(
                id=_slug(f"{feature_type}-{e.get('ID', i)}"),
                type=feature_type,
                name=name,
                position=_location(e),
                meta=meta,
                collected=collected,
            )
        )
    return features


def normalize_belts(belts_raw: Iterable[Raw]) -> list[BeltPath]:
    """Map FRM ``getBelts`` entries to :class:`BeltPath` polylines.

    Uses the belt's ``SplineData`` (world-space cm points along the belt) when
    present, falling back to the straight ``location0`` → ``location1`` segment.
    Entries without two usable points are dropped.
    """
    belts: list[BeltPath] = []
    for i, b in enumerate(belts_raw):
        points = [
            Position(x=_num(p.get("x")), y=_num(p.get("y")), z=_num(p.get("z")))
            for p in b.get("SplineData") or []
            if isinstance(p, dict)
        ]
        if len(points) < 2:
            ends = [b.get("location0"), b.get("location1")]
            points = [
                Position(x=_num(p.get("x")), y=_num(p.get("y")), z=_num(p.get("z")))
                for p in ends
                if isinstance(p, dict)
            ]
        if len(points) < 2:
            continue
        ipm = b.get("ItemsPerMinute")
        belts.append(
            BeltPath(
                id=_slug(f"belt-{b.get('ID', i)}"),
                name=str(b.get("Name") or "Conveyor Belt"),
                class_name=str(b.get("ClassName") or "Build_ConveyorBeltMk1_C"),
                points=points,
                items_per_minute=_num(ipm) if ipm is not None else None,
            )
        )
    return belts


def _channel(value: Any) -> int:
    """Coerce one color channel to 0–255. Accepts 0–1 floats or 0–255 numbers."""
    f = _num(value)
    if 0.0 < f <= 1.0:
        f *= 255.0
    return max(0, min(255, round(f)))


def _color_to_hex(value: Any) -> str | None:
    """Normalize an FRM color value into ``#rrggbb``, or None if unrecognized.

    FRM paint data appears in several shapes across versions/mods: a hex string
    (``"#RRGGBB"`` / ``"RRGGBBAA"``), an ``{R,G,B}`` object of 0–1 floats or
    0–255 ints, or an ``[r, g, b]`` list. Anything else degrades to None.
    """
    if isinstance(value, str):
        s = value.strip().lstrip("#")
        if len(s) in (6, 8) and all(c in "0123456789abcdefABCDEF" for c in s):
            return f"#{s[:6].lower()}"
        return None
    if isinstance(value, dict):
        r, g, b = (value.get("R", value.get("r")),
                   value.get("G", value.get("g")),
                   value.get("B", value.get("b")))
        if r is None or g is None or b is None:
            return None
        return f"#{_channel(r):02x}{_channel(g):02x}{_channel(b):02x}"
    if isinstance(value, (list, tuple)) and len(value) >= 3:
        return f"#{_channel(value[0]):02x}{_channel(value[1]):02x}{_channel(value[2]):02x}"
    return None


def _swatch_hex(b: Raw) -> str | None:
    """Primary paint-swatch color of a building as ``#rrggbb``, or None.

    Reads the customization color the player painted the building with, checking
    the field names FRM exposes it under (a ``ColorSlot`` object, or a top-level
    ``PrimaryColor`` / ``Color``). The primary color drives the map pin's ring.
    """
    slot = b.get("ColorSlot") or b.get("colorSlot")
    candidates: list[Any] = []
    if isinstance(slot, dict):
        candidates += [slot.get("PrimaryColor"), slot.get("primaryColor"),
                       slot.get("Primary"), slot.get("primary")]
    candidates += [b.get("PrimaryColor"), b.get("primaryColor"),
                   b.get("Color"), b.get("color")]
    for candidate in candidates:
        if candidate is not None:
            hex_color = _color_to_hex(candidate)
            if hex_color:
                return hex_color
    return None


def _building_status(b: Raw) -> str:
    """Stable per-building status: operational / caution (idle) / error.

    A coarse bucket (not a live percentage) so feature equality stays stable
    between polls and ``world.features`` is only re-published on real change.
    """
    power_info = b.get("PowerInfo") or b.get("powerInfo") or {}
    if bool(power_info.get("FuseTriggered")) or b.get("IsConfigured") is False:
        return "error"
    productivity = _num(b.get("Productivity", b.get("productivity")), _num(b.get("ManuSpeed")))
    if bool(b.get("IsProducing", productivity > 0)):
        return "operational"
    return "caution"


def _building_meta(b: Raw, name: str) -> dict[str, str | float | int]:
    """Assemble the ``meta`` dict for one building feature."""
    meta: dict[str, str | float | int] = {"kind": _slug(name)}
    # Class + yaw let the frontend draw the building's real footprint outline
    # (SCIM detailed models are keyed by short UE class name).
    class_name = str(b.get("ClassName") or "")
    if class_name:
        meta["class_name"] = class_name
    loc = b.get("location") or b.get("Location") or {}
    if isinstance(loc, dict) and loc.get("rotation") is not None:
        meta["rotation"] = _num(loc.get("rotation"))
    meta["status"] = _building_status(b)
    # Paint-swatch color drives the map pin's ring (see utils/mapIcons.ts).
    swatch = _swatch_hex(b)
    if swatch:
        meta["color"] = swatch
    power_info = b.get("PowerInfo") or b.get("powerInfo") or {}
    power = round(_num(power_info.get("PowerConsumed")))
    if power > 0:
        meta["power_mw"] = power
    outputs = [
        str(o.get("Name") or o.get("item") or "") for o in b.get("production", []) or []
    ]
    outputs = [o for o in outputs if o]
    if outputs:
        meta["produces"] = ", ".join(dict.fromkeys(outputs))
    return meta


def _building_feature(feature_type: FeatureType, index: int, b: Raw) -> MapFeature:
    """Build one building map feature (factory / power_plant marker)."""
    name = str(b.get("Name") or "Factory")
    return MapFeature(
        id=_slug(f"{feature_type}-{b.get('ID', index)}"),
        type=feature_type,
        name=name,
        position=_location(b),
        meta=_building_meta(b, name),
    )


def _building_features(
    factory_raw: Iterable[Raw],
    generators_raw: Iterable[Raw],
    extractor_raw: Iterable[Raw] = (),
) -> list[MapFeature]:
    """Production/extraction buildings (``factory``) and generators (``power_plant``).

    Miners and oil/water/well extractors come from FRM's ``getExtractor`` feed and
    render as ``factory`` markers alongside manufacturers. Every building is its
    own map feature — the id must be unique per building (FRM ``ID`` when present,
    else the enumeration index) so same-class buildings don't collide into one
    marker.
    """
    typed: list[tuple[FeatureType, list[Raw]]] = [
        ("factory", [*factory_raw, *extractor_raw]),
        ("power_plant", list(generators_raw)),
    ]
    return [
        _building_feature(feature_type, i, b)
        for feature_type, entries in typed
        for i, b in enumerate(entries)
    ]


def normalize_world(
    players_raw: Iterable[Raw],
    factory_raw: Iterable[Raw],
    nodes_raw: Iterable[Raw],
    *,
    artifacts_raw: Iterable[Raw] | None = None,
    slugs_raw: Iterable[Raw] | None = None,
    drop_pods_raw: Iterable[Raw] | None = None,
    belts_raw: Iterable[Raw] | None = None,
    cables_raw: Iterable[Raw] | None = None,
    pipes_raw: Iterable[Raw] | None = None,
    generators_raw: Iterable[Raw] | None = None,
    extractor_raw: Iterable[Raw] | None = None,
    source: str = "frm",
) -> WorldSnapshot:
    """Build a world snapshot from FRM players / factories / resource nodes.

    Pickups are optional: *artifacts_raw* (Somersloops/Mercer Spheres) and
    *slugs_raw* (power slugs) render as artifacts; *drop_pods_raw* as crash-site
    wrecks. *generators_raw* render as ``power_plant`` buildings; *extractor_raw*
    (miners, oil/water/well extractors) render as ``factory`` markers; *belts_raw*
    / *cables_raw* / *pipes_raw* become the belt / power-line / pipeline path
    layers. FRM 1.5.x exposes no endpoint for wild food or foundations, so
    those stay empty on live data.
    """
    players = [
        PlayerInfo(
            id=_slug(str(p.get("Name") or f"player-{i}")),
            name=str(p.get("Name") or f"Player {i}"),
            position=_location(p),
            online=True,
        )
        for i, p in enumerate(players_raw, start=1)
    ]
    features = _building_features(factory_raw, generators_raw or [], extractor_raw or [])
    for node in nodes_raw:
        base = str(node.get("Name") or node.get("ResourceForm") or "Node")
        purity = str(node.get("Purity") or "normal").lower()
        occupied = bool(node.get("Exploited") or node.get("Occupied"))
        resource = _slug(base)
        features.append(
            MapFeature(
                # Purity is shown in the name (e.g. "Iron Ore (Pure)") and kept in
                # meta for the purity filter; ``resource`` stays the base slug so
                # the resource filter still groups nodes regardless of purity.
                id=_slug(f"{base}-{node.get('ID', len(features))}"),
                type=_node_feature_type(node, resource),
                name=f"{base} ({purity.capitalize()})",
                position=_location(node),
                meta={"resource": resource, "purity": purity},
                occupied=occupied,
            )
        )
    features += _pickup_features(artifacts_raw or [], "artifact", default_name="Artifact")
    features += _pickup_features(slugs_raw or [], "artifact", default_name="Power Slug")
    features += _pickup_features(
        drop_pods_raw or [], "wreck", default_name="Crash Site", collected_key="Looted"
    )
    return WorldSnapshot(
        generated_at=datetime.now(UTC),
        source=source,
        players=players,
        features=features,
        belts=normalize_belts(belts_raw or []),
        cables=normalize_belts(cables_raw or []),
        pipes=normalize_belts(pipes_raw or []),
    )


def normalize_logistics(
    stations_raw: Iterable[Raw], trains_raw: Iterable[Raw], *, source: str = "frm"
) -> LogisticsSnapshot:
    """Build a logistics snapshot from FRM train stations and trains."""
    nodes = [
        LogisticsNode(
            id=_slug(str(s.get("Name") or f"station-{i}")),
            name=str(s.get("Name") or f"Station {i}"),
            type="station",
            position=_location(s),
        )
        for i, s in enumerate(stations_raw, start=1)
    ]
    trains = [
        TrainInfo(
            id=_slug(str(t.get("Name") or f"train-{i}")),
            name=str(t.get("Name") or f"Train {i}"),
            line=str(t.get("TrainStation") or "unknown"),
            position=_location(t),
            loaded_item=None,
        )
        for i, t in enumerate(trains_raw, start=1)
    ]
    return LogisticsSnapshot(
        generated_at=datetime.now(UTC),
        source=source,
        nodes=nodes,
        routes=[],  # belt/pipe throughput is not exposed by FRM; rail routes TBD
        trains=trains,
        summary=LogSummary(route_count=0, node_count=len(nodes)),
    )
