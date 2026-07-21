"""The admin cheat catalog: every action the admin panel exposes.

The catalog is pure data — the frontend renders it generically and the
:class:`~app.services.admin_cheats.AdminCheatService` dispatches executed
actions to the configured game-side command endpoint. Adding a cheat is a
catalog entry here plus a handler in the companion game mod; no UI changes.
"""

from __future__ import annotations

from typing import Any

from app.schemas.admin import CheatAction, CheatCategory, CheatParam, CheatSection


def _p(name: str, label: str, type_: str = "number", **kw: Any) -> CheatParam:
    return CheatParam(name=name, label=label, type=type_, **kw)


def _slider(name: str, label: str, min_: float, max_: float, step: float, default: float,
            unit: str | None = None) -> CheatParam:
    return CheatParam(name=name, label=label, type="slider", min=min_, max=max_,
                      step=step, default=default, unit=unit)


def _btn(id_: str, label: str, *params: CheatParam, danger: bool = False,
         hint: str | None = None) -> CheatAction:
    return CheatAction(id=id_, label=label, control="button", params=list(params),
                       danger=danger, hint=hint)


def _tgl(id_: str, label: str, *params: CheatParam, hint: str | None = None) -> CheatAction:
    return CheatAction(id=id_, label=label, control="toggle", params=list(params), hint=hint)


def _sec(id_: str, label: str, *actions: CheatAction) -> CheatSection:
    return CheatSection(id=id_, label=label, actions=list(actions))


# Unlocks live on the shared session (research/schematics), not a player.
_SHARED_UNLOCKS = {
    "player.unlock_all_recipes",
    "player.unlock_milestone",
    "player.unlock_mam",
    "player.unlock_awesome_shop",
}
# Visual-only overlays: rendered for one player, mutate nothing shared.
_PLAYER_VISUALS = {
    "power.highlight_overloaded",
    "belts.highlight_bottlenecks",
    "pipes.pressure_map",
    "radiation.visualize",
    "appearance.hide_foundations",
    "appearance.transparent_buildings",
    "appearance.xray",
}


def _classify(category_id: str, section_id: str, action: CheatAction) -> None:
    """Set ``scope`` (player selector) and ``affects_all`` (shared-state badge).

    Defaults are conservative: anything that mutates state shared by the whole
    session is flagged ``affects_all``; anything acting on a single pioneer (or
    drawing a per-player overlay) is ``scope="player"``.
    """
    if action.id in _SHARED_UNLOCKS:
        action.scope, action.affects_all = "world", True
    elif action.id in _PLAYER_VISUALS or category_id == "analysis" or category_id == "player":
        action.scope, action.affects_all = "player", False
    elif category_id == "building" and section_id == "placement":
        # Build-gun rule toggles apply to one player's build gun.
        action.scope, action.affects_all = "player", False
    elif category_id == "inspector":
        action.scope, action.affects_all = "world", False
    else:
        # Mass building, delete tools, power, logistics, trains, drones, world,
        # creatures, radiation, appearance painting: shared state.
        action.scope, action.affects_all = "world", True


_AREA = _p("area", "Area (min/max coords as x1,y1,x2,y2)", "text")
_CREATURES = ["Hog", "Alpha Hog", "Spitter", "Alpha Spitter", "Stinger", "Elite Stinger",
              "Crab Hatcher", "Lizard Doggo", "Flying Crab", "Boss: Elite Gas Stinger",
              "Boss: Johnny"]
_BELT_TIERS = ["Mk.1", "Mk.2", "Mk.3", "Mk.4", "Mk.5", "Mk.6"]
_MINER_TIERS = ["Mk.1", "Mk.2", "Mk.3"]
_PIPE_TIERS = ["Mk.1", "Mk.2"]
_POLE_TIERS = ["Mk.1", "Mk.2", "Mk.3"]


def build_catalog() -> list[CheatCategory]:
    """Build the full cheat category tree (stateless; safe to call per request)."""
    categories = [
        CheatCategory(id="player", label="Player Cheats", icon="🛠️", sections=[
            _sec("inventory", "Inventory",
                 _btn("player.spawn_item", "Spawn item",
                      _p("item", "Item", "item"),
                      _p("quantity", "Quantity", "number", min=1, max=100000, default=100)),
                 _btn("player.spawn_full_stacks", "Spawn full stacks",
                      _p("item", "Item", "item"),
                      _p("stacks", "Stacks", "number", min=1, max=100, default=1)),
                 _btn("player.unlock_all_recipes", "Unlock all recipes", danger=True),
                 _btn("player.unlock_milestone", "Unlock milestone",
                      _p("tier", "Tier", "number", min=0, max=9, default=1),
                      _p("milestone", "Milestone name", "text")),
                 _btn("player.unlock_mam", "Unlock all MAM research", danger=True),
                 _btn("player.unlock_awesome_shop", "Unlock Awesome Shop items", danger=True),
                 _btn("player.give_hard_drives", "Give all hard drives",
                      _p("count", "Count", "number", min=1, max=200, default=100)),
                 _btn("player.clear_inventory", "Clear inventory", danger=True),
                 _btn("player.save_inventory_preset", "Save inventory as preset",
                      _p("name", "Preset name", "text"),
                      hint="Snapshots the current player inventory server-side."),
                 _btn("player.load_inventory_preset", "Load inventory preset",
                      _p("name", "Preset name", "text"))),
            _sec("equipment", "Equipment",
                 _btn("player.equip_gear", "Equip gear", _p("gear", "Gear item", "item")),
                 _tgl("player.infinite_jetpack", "Infinite jetpack fuel"),
                 _tgl("player.infinite_hoverpack", "Infinite hover pack range"),
                 _tgl("player.infinite_gas_filters", "Infinite gas filters"),
                 _tgl("player.infinite_parachute", "Infinite parachute"),
                 _tgl("player.infinite_ammo", "Infinite ammo"),
                 _tgl("player.infinite_health", "Infinite health",
                      hint="Take no damage — supersedes a separate god mode.")),
            _sec("movement", "Movement",
                 _tgl("player.fly", "Fly mode"),
                 _tgl("player.noclip", "No clip"),
                 _btn("player.teleport_coords", "Teleport to coordinates",
                      _p("coords", "Coordinates", "coords")),
                 _btn("player.teleport_waypoint", "Teleport to waypoint",
                      _p("waypoint", "Waypoint name", "text")),
                 # "player" is reserved for the target selector; the destination
                 # pioneer is "to_player".
                 _btn("player.teleport_player", "Teleport to player",
                      _p("to_player", "Teleport to (player name)", "text")),
                 _btn("player.save_teleport", "Save teleport location",
                      _p("name", "Location name", "text"),
                      _p("coords", "Coordinates", "coords")),
                 _tgl("player.gravity", "Custom gravity",
                      _slider("scale", "Gravity", 0.0, 3.0, 0.05, 1.0, "×")),
                 _tgl("player.jump_height", "Custom jump height",
                      _slider("scale", "Jump height", 0.5, 10.0, 0.5, 1.0, "×")),
                 _tgl("player.time_scale", "Time scale",
                      _slider("scale", "Time scale", 0.05, 10.0, 0.05, 1.0, "×"),
                      hint="Below 1× is slow motion, above is fast-forward.")),
            _sec("owner", "Owner Tools",
                 _btn("player.heal", "Heal to full"),
                 _btn("player.revive", "Revive"),
                 _btn("player.reveal_map", "Reveal whole map"),
                 _btn("player.collect_crates", "Collect dropped crates"),
                 _btn("player.give_coupons", "Give AWESOME coupons",
                      _p("count", "Coupons", "number", min=1, max=10000, default=100)),
                 _btn("player.unlock_inventory_slots", "Unlock inventory slots",
                      _p("count", "Slots", "number", min=1, max=24, default=24)),
                 _btn("player.unlock_arm_slots", "Unlock arm/hand slots",
                      _p("count", "Slots", "number", min=1, max=4, default=3)),
                 _btn("player.complete_research", "Complete active research"),
                 _btn("player.next_game_phase", "Advance game phase", danger=True),
                 _btn("player.promote_admin", "Promote me to server admin")),
        ]),
        CheatCategory(id="building", label="Building Cheats", icon="🏭", sections=[
            _sec("placement", "Placement",
                 _tgl("build.unlimited_distance", "Unlimited build distance"),
                 _tgl("build.ignore_terrain", "Ignore terrain restrictions"),
                 _tgl("build.ignore_supports", "Ignore support requirements"),
                 _tgl("build.infinite_zoop", "Infinite zoop"),
                 _tgl("build.infinite_blueprint", "Infinite blueprint size"),
                 _tgl("build.custom_rotation", "Rotate by custom angle",
                      _slider("degrees", "Angle", 1, 90, 1, 15, "°")),
                 _tgl("build.mirror", "Mirror placement")),
            _sec("mass", "Mass Building (select an area)",
                 _btn("build.upgrade_belts", "Upgrade all belts", _AREA,
                      _p("tier", "Target tier", "select", options=_BELT_TIERS, default="Mk.6")),
                 _btn("build.upgrade_lifts", "Upgrade lifts", _AREA,
                      _p("tier", "Target tier", "select", options=_BELT_TIERS, default="Mk.6")),
                 _btn("build.upgrade_miners", "Upgrade miners", _AREA,
                      _p("tier", "Target tier", "select", options=_MINER_TIERS, default="Mk.3")),
                 _btn("build.upgrade_pipes", "Upgrade pipes", _AREA,
                      _p("tier", "Target tier", "select", options=_PIPE_TIERS, default="Mk.2")),
                 _btn("build.upgrade_poles", "Upgrade power poles", _AREA,
                      _p("tier", "Target tier", "select", options=_POLE_TIERS, default="Mk.3")),
                 _btn("build.replace_buildings", "Replace buildings", _AREA,
                      _p("from", "Replace", "text"), _p("to", "With", "text"), danger=True),
                 _btn("build.copy_recipes", "Copy recipes", _AREA,
                      _p("recipe", "Recipe", "text")),
                 _btn("build.copy_clocks", "Copy clock speeds", _AREA,
                      _slider("clock", "Clock speed", 1, 250, 1, 100, "%")),
                 _btn("build.copy_colors", "Copy colors", _AREA,
                      _p("swatch", "Swatch", "text")),
                 _btn("build.copy_materials", "Copy materials", _AREA,
                      _p("material", "Material", "text"))),
            _sec("delete", "Delete Tools",
                 _btn("build.delete_factory", "Delete entire factory", danger=True,
                      hint="Removes every player-built structure. Undo keeps one snapshot."),
                 _btn("build.delete_floor", "Delete floor",
                      _p("floor", "Floor (z-level)", "number"), danger=True),
                 _btn("build.delete_foundation_type", "Delete foundation type",
                      _p("type", "Foundation type", "text"), danger=True),
                 _btn("build.delete_belt_network", "Delete conveyor network", _AREA, danger=True),
                 _btn("build.delete_pipe_network", "Delete pipe network", _AREA, danger=True),
                 _btn("build.delete_power_network", "Delete power network", _AREA, danger=True),
                 _btn("build.delete_decorations", "Delete decorations only", _AREA, danger=True),
                 _btn("build.delete_lights", "Delete lights only", _AREA, danger=True),
                 _btn("build.undo", "Undo last delete",
                      hint="Restores the snapshot taken by the most recent delete.")),
        ]),
        CheatCategory(id="power", label="Power Controls", icon="⚡", sections=[
            _sec("power", "Power",
                 _tgl("power.infinite", "Infinite power"),
                 _btn("power.recharge_batteries", "Recharge all batteries"),
                 _btn("power.fill_generators", "Fill all generators"),
                 _btn("power.fill_fuel", "Fill all fuel"),
                 _btn("power.set_grid_load", "Set grid load",
                      _slider("load", "Load", 0, 100, 1, 50, "%")),
                 _btn("power.blackout", "Simulate blackout", danger=True),
                 _tgl("power.highlight_overloaded", "Highlight overloaded circuits")),
        ]),
        CheatCategory(id="logistics", label="Logistics", icon="📦", sections=[
            _sec("belts", "Belts",
                 _btn("belts.fill", "Instantly fill belts", _AREA),
                 _btn("belts.empty", "Empty belts", _AREA),
                 _btn("belts.reverse", "Reverse belts", _AREA),
                 _tgl("belts.pause", "Pause belts"),
                 _btn("belts.set_speed", "Change belt speed", _AREA,
                      _slider("scale", "Speed", 0.1, 10, 0.1, 1, "×")),
                 _tgl("belts.highlight_bottlenecks", "Highlight bottlenecks")),
            _sec("pipes", "Pipes",
                 _btn("pipes.fill", "Fill pipes", _AREA),
                 _btn("pipes.drain", "Drain pipes", _AREA),
                 _btn("pipes.change_fluid", "Change fluid", _AREA,
                      _p("fluid", "Fluid", "item")),
                 _tgl("pipes.freeze", "Freeze flow"),
                 _tgl("pipes.pressure_map", "Show pressure map")),
            _sec("storage", "Storage",
                 _btn("storage.fill", "Fill containers", _AREA, _p("item", "Item", "item")),
                 _btn("storage.empty", "Empty containers", _AREA, danger=True),
                 _btn("storage.replace", "Replace contents", _AREA,
                      _p("item", "New item", "item"), danger=True),
                 _tgl("storage.lock", "Lock inventories"),
                 _btn("storage.duplicate", "Duplicate storage", _AREA)),
        ]),
        CheatCategory(id="trains", label="Train Controls", icon="🚂", sections=[
            _sec("trains", "Trains",
                 _btn("trains.spawn", "Spawn train", _p("station", "At station", "text")),
                 _btn("trains.delete", "Delete train", _p("train", "Train name", "text"),
                      danger=True),
                 _btn("trains.teleport", "Teleport train", _p("train", "Train name", "text"),
                      _p("station", "To station", "text")),
                 _tgl("trains.pause", "Pause all trains"),
                 _btn("trains.skip_station", "Skip station", _p("train", "Train name", "text")),
                 _btn("trains.force_dock", "Force docking", _p("train", "Train name", "text")),
                 _btn("trains.refuel", "Refuel all trains"),
                 _btn("trains.empty_cargo", "Empty cargo", _p("train", "Train name", "text"),
                      danger=True),
                 _btn("trains.fill_cargo", "Fill cargo", _p("train", "Train name", "text"),
                      _p("item", "Item", "item")),
                 _btn("trains.clone_schedule", "Clone schedule",
                      _p("from", "From train", "text"), _p("to", "To train", "text"))),
        ]),
        CheatCategory(id="drones", label="Drone Controls", icon="🚁", sections=[
            _sec("drones", "Drones",
                 _btn("drones.spawn", "Spawn drone", _p("port", "At drone port", "text")),
                 _btn("drones.recharge", "Recharge all batteries"),
                 _btn("drones.force_deliveries", "Force deliveries"),
                 _tgl("drones.pause", "Pause routes"),
                 _btn("drones.reset_paths", "Reset paths"),
                 _btn("drones.duplicate_route", "Duplicate route",
                      _p("from", "From port", "text"), _p("to", "To port", "text"))),
        ]),
        CheatCategory(id="world", label="World Controls", icon="🌎", sections=[
            _sec("time", "Time",
                 _btn("world.time_morning", "Morning"),
                 _btn("world.time_noon", "Noon"),
                 _btn("world.time_sunset", "Sunset"),
                 _btn("world.time_midnight", "Midnight"),
                 _tgl("world.freeze_time", "Freeze time"),
                 _tgl("world.time_multiplier", "Time multiplier",
                      _slider("scale", "Multiplier", 0.1, 50, 0.1, 1, "×"))),
            _sec("environment", "Environment",
                 _btn("world.remove_foliage", "Remove foliage", _AREA, danger=True),
                 _btn("world.regrow_foliage", "Regrow foliage", _AREA),
                 _btn("world.clear_rocks", "Clear rocks", _AREA, danger=True),
                 _btn("world.respawn_resources", "Respawn resources"),
                 _btn("world.respawn_creatures", "Respawn creatures"),
                 _btn("world.kill_creatures", "Kill all creatures", danger=True)),
        ]),
        CheatCategory(id="creatures", label="Creature Controls", icon="👾", sections=[
            _sec("spawn", "Spawn",
                 _btn("creatures.spawn", "Spawn creature",
                      _p("creature", "Creature", "select", options=_CREATURES),
                      _p("count", "Count", "number", min=1, max=50, default=1),
                      _p("behavior", "Behavior", "select",
                         options=["Friendly", "Hostile", "Passive", "Aggressive"],
                         default="Passive"))),
            _sec("options", "Options",
                 _tgl("world.disable_arachnids", "Arachnophobia mode (replace spiders)"),
                 _tgl("creatures.infinite_health", "Creatures: infinite health"),
                 _tgl("creatures.one_shot", "One-shot kill")),
        ]),
        CheatCategory(id="radiation", label="Radiation", icon="☢️", sections=[
            _sec("radiation", "Radiation",
                 _tgl("radiation.disable", "Disable radiation"),
                 _tgl("radiation.multiplier", "Radiation multiplier",
                      _slider("scale", "Multiplier", 0, 10, 0.1, 1, "×")),
                 _tgl("radiation.visualize", "Visualize radiation"),
                 _btn("radiation.remove_waste", "Remove nuclear waste", danger=True),
                 _btn("radiation.spawn_waste", "Spawn waste",
                      _p("quantity", "Quantity", "number", min=1, max=1000, default=100))),
        ]),
        CheatCategory(id="analysis", label="Factory Analysis", icon="📈", sections=[
            _sec("highlight", "Highlight buildings",
                 _tgl("analysis.idle", "Idle buildings"),
                 _tgl("analysis.underclocked", "Underclocked"),
                 _tgl("analysis.overclocked", "Overclocked"),
                 _tgl("analysis.backed_up", "Backed up"),
                 _tgl("analysis.starving", "Starving"),
                 _tgl("analysis.no_power", "No power"),
                 _tgl("analysis.wrong_recipe", "Wrong recipe"),
                 _tgl("analysis.disconnected", "Disconnected"),
                 _tgl("analysis.bottlenecks", "Bottlenecks")),
        ]),
        CheatCategory(id="inspector", label="Inspector", icon="🔍", sections=[
            _sec("inspector", "Building inspector",
                 _btn("inspector.inspect", "Inspect building",
                      _p("building", "Building ID or name", "text"),
                      hint="Returns inventory, I/O, recipe, clock, power draw, efficiency, "
                           "buffers, and production history for one building.")),
        ]),
        CheatCategory(id="appearance", label="Appearance", icon="🎨", sections=[
            _sec("appearance", "Appearance",
                 _btn("appearance.paint", "Paint factory", _AREA,
                      _p("color", "Color (hex)", "text")),
                 _btn("appearance.random_colors", "Random colors", _AREA),
                 _btn("appearance.corporate_theme", "Corporate theme", _AREA,
                      _p("theme", "Theme", "select",
                         options=["FICSIT Orange", "Steel Grey", "Midnight", "Safety Yellow",
                                  "SpiffCo Blue"])),
                 _tgl("appearance.night_lights", "Night mode lights"),
                 _tgl("appearance.hide_foundations", "Hide foundations"),
                 _tgl("appearance.transparent_buildings", "Transparent buildings"),
                 _tgl("appearance.xray", "X-ray mode")),
        ]),
    ]
    for category in categories:
        for section in category.sections:
            for action in section.actions:
                _classify(category.id, section.id, action)
    return categories
