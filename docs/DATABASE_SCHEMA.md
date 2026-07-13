# Database Schema

Two kinds of data: **application tables** (SQLite/SQLAlchemy) and **static game
data** (JSON in `database/data/`).

## Application tables

### `app_settings`

| Column | Type | Notes |
|---|---|---|
| `key` | TEXT PK (≤128) | Dotted setting key, e.g. `ui.theme` |
| `value` | TEXT | JSON-encoded value |
| `created_at` / `updated_at` | DATETIME | UTC, maintained by `TimestampMixin` |

History/telemetry tables (production samples, power samples, machine states)
arrive with Phase 2 and will be introduced together with Alembic migrations.

### `factory_plans` (Phase 4)

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `name` | TEXT (≤128) | |
| `description` | TEXT | |
| `version` | INTEGER | Current version number (starts at 1) |
| `layout` | JSON | `{grid, placements}` — the current editable layout |
| `created_at` / `updated_at` | DATETIME | UTC, via `TimestampMixin` |

### `plan_versions` (Phase 4)

Append-only snapshot per save; enables non-destructive revert.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `plan_id` | INTEGER FK → `factory_plans.id` | `ON DELETE CASCADE` |
| `version` | INTEGER | Monotonic per plan |
| `comment` | TEXT (≤256) | e.g. `initial`, `edit`, `revert to v2` |
| `layout` | JSON | Frozen layout for this version |
| `created_at` / `updated_at` | DATETIME | UTC, via `TimestampMixin` |

### `blueprints` (Phase 8)

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `name` | TEXT (≤128) | |
| `description` | TEXT | |
| `category` | TEXT (≤64), indexed | e.g. `smelting`, `power` (default `general`) |
| `tags` | JSON | List of tag strings |
| `favorite` | BOOLEAN | |
| `data` | JSON | Reusable payload (layout / recipe fragment) |
| `created_at` / `updated_at` | DATETIME | UTC, via `TimestampMixin` |

## Static game data (JSON)

Conventions: IDs are stable kebab-case slugs; item/fluid rates are **per
minute**; power is **MW**; world positions are **centimeters** (Unreal units).

### `items.json`
`{ id, name, category (ore|ingot|part|fluid|…), stack_size, is_fluid, sink_points }`

### `recipes.json` / `alternate_recipes.json`
`{ id, name, machine (building id), duration_seconds, inputs: [{item, rate}], outputs: [{item, rate}] }`
Alternates add `unlock: "hard-drive"`.

### `buildings.json`
`{ id, name, category (production|extraction), power_mw (consumption), inputs, outputs, footprint {width,length} }`

### `build_costs.json`
`{ building, cost: { <item-id>: quantity } }`

### `power_buildings.json`
`{ id, name, power_mw (output), fuel, fuel_rate, requires_water, water_rate?, capacity_mwh? }`

### `resources.json`
`{ id, name, extractor (miner|oil-extractor|water-extractor|resource-well), is_fluid }`

### `resource_nodes.json`
`{ id, resource, purity (impure|normal|pure), position {x,y,z}, region }` —
purity multipliers: 0.5 / 1.0 / 2.0.

### `collectibles.json`
`{ id, category (artifact|collectible|wreck), name, position {x,y,z}, meta {kind, region, loot?} }`
— collected state is per-save (live data), never stored here.

### `transportation.json`
Belts/pipes: `{ id, name, rate }`. Vehicles: `{ id, name, capacity_slots, fuel }`.

### `machines.json`
`{ id, building, min_clock, max_clock, power_exponent, somersloop_slots, base_rate? }`
Power at clock *c*: `power_mw * c^power_exponent`. Each filled somersloop slot
multiplies output (and squares power) per game rules — exact formulas land with
the Phase 5 planner.

The shipped files are seed subsets; the full dataset is imported from the
game's `Docs.json` by a planned `scripts/import_game_data.py`.
