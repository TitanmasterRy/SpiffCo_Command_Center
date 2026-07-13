# Project State

Last updated: **2026-07-13** · Current milestone: **All 12 spec phases complete** — SCIM-parity pass underway; post-spec hardening backlog remains

Snapshot of what exists and works versus what remains. Companion docs:
[docs/ROADMAP.md](docs/ROADMAP.md) (phase plan) and
[docs/KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md) (deliberate gaps).

## 🆕 SCIM-parity pass (post-spec, in progress)

Making the map / planner / calculator more like satisfactory-calculator.com (SCIM),
on the **live-FRM** data path. Delivered so far:

- **Full game-data importer** (`scripts/import_game_data.py`): parses the game's
  `Docs.json` (UTF-16) and regenerates `items` / `resources` / `recipes` /
  `alternate_recipes` / `buildings` / `build_costs` / `machines` /
  `power_buildings` at full catalog scale — byte-shape-compatible with the seed
  files, so the solver/planner/loaders need no changes (seed subset → ~800
  recipes). Verified end-to-end against a synthetic `Docs.json`; validates against
  `RecipeInfo`/`ItemInfo`/`BuildingInfo`. **Run it with the real file to populate
  data** (`--docs <path>`, `--dry-run` to preview). Does **not** touch world
  positions — `resource_nodes.json` / `collectibles.json` coordinates and exact
  building footprints need map-data tooling (no coordinates exist in `Docs.json`).
- **Planner network-graph view** (`components/ProductionGraph.tsx`,
  `utils/productionGraph.ts`): SCIM-style draggable/zoomable left-to-right DAG of
  the production chain (shared items merge into one node with summed rate), plus
  **Tree / Network graph / Items / Buildings** view tabs on the planner. Pure
  layout util unit-tested (`tests/productionGraph.test.ts`).
- **Map coordinate readout**: live cursor game-world (cm) coordinates overlay on
  the World Map (`CursorTracker`). Biome text deferred — needs region-polygon data.
- **Map per-building rendering**: `normalize_world` now gives every building a
  **unique** feature id (was colliding same-class buildings into one marker) and
  attaches `produces` meta for popups. Regression-tested.
- **New map layer types**: `resource_well`, `geyser` added to `FeatureType`
  (schema + frontend styles/toggles) — render when data provides them.
- **`_slug` hardened** to emit DOM-safe kebab ids (splits on `_`/`.`/space), which
  also fixed a previously-broken, uncommitted pickups test.

Verified: backend pytest **93/93**, frontend vitest **43/43**, `tsc`/production
build clean, ruff + mypy clean on all changed files.

Not in this pass (by decision): save-file editor (reverses live-only; risky
`.sav` writes), tiled multi-zoom basemap (single game-image overlay already
backs the map), and decorative rock/cave/road layers (bulk position data needed).

## ✅ Complete

### Phase 1 — Foundation

**Backend** (`backend/`, FastAPI, Python 3.11+, fully async, 19/19 tests passing)
- Typed configuration: `pydantic-settings`, `SPIFFCO_` env prefix, `.env` support (`app/config/settings.py`).
- Structured logging: console + optional rotating file handler (`app/config/logging_config.py`).
- Error handling: `AppError` hierarchy + handlers producing one JSON error envelope for all failures (`app/errors.py`).
- Database: async SQLAlchemy 2.0 on SQLite (aiosqlite), URL-swappable to PostgreSQL, schema auto-created at startup (`app/database/engine.py`).
- REST API under `/api/v1`: health, info, settings CRUD; OpenAPI docs at `/docs`.
- WebSocket server at `/ws`: subscribe/unsubscribe/ping protocol with wildcard topics (`app/api/ws.py`).
- Event bus: in-process pub/sub with bounded queues — slow consumers drop their own oldest events (`app/services/event_bus.py`).
- Scheduler: asyncio periodic jobs; a failing job logs and retries, never kills others (`app/workers/scheduler.py`).
- FRM connector **interface** (contract only) in `app/connectors/frm/`.
- Domain package scaffolds with phase docstrings: planner, power, logistics, analytics, advisors, blueprints, resources, world, storage, simulation.

**Frontend** (`frontend/`, React 18 + TS strict + Vite + Tailwind, builds clean, 8/8 tests passing)
- Dark industrial theme, sidebar/topbar layout, routes for all planned pages.
- Typed API client with error envelope handling; auto-reconnecting WebSocket client (exponential backoff, resubscribe on reconnect).
- TanStack Query for server state; Zustand connection store; connection/FRM badges in the top bar.

**Infrastructure & docs**
- Docker Compose (backend + nginx frontend, persistent volume); Dockerfiles for both services.
- Dev scripts (`scripts/dev.ps1`, `scripts/dev.sh`).
- Full docs set: ARCHITECTURE (with trade-offs), API_REFERENCE, DATABASE_SCHEMA, DEVELOPER_GUIDE, DEPLOYMENT, PLUGIN_GUIDE (design spec), CODING_STANDARDS, ROADMAP, KNOWN_LIMITATIONS.
- Root files: README, LICENSE (MIT), CHANGELOG, CONTRIBUTING, CLAUDE.md, `.env.example`, `.gitignore`.
- Seed game data in `database/data/`: items, recipes, alternate recipes, buildings, build costs, power buildings, resources, resource nodes, transportation, machines.

### Phase 2 — Dashboard

**Backend**
- `GameStateProvider` protocol + `SimulatedGameProvider` (seedable random-walk mid-game telemetry) in `app/simulation/provider.py`.
- `GameStateService` (`app/services/game_state.py`): refresh every poll interval (default 5 s), publishes full snapshots on WS topic `dashboard.snapshot`, records history every 30 s.
- History tables `power_samples`, `production_samples` (`app/models/history.py`).
- Endpoints: `GET /api/v1/dashboard`, `/dashboard/history/power`, `/dashboard/history/production/{item}`.
- Rule-based alerts (battery low, power headroom <10%, factory below target, storage >95%) — precursor to the Phase 10 advisor.

**Frontend**
- Dashboard page: stat tiles (power, battery, machines, efficiency), Recharts power-history chart (produced/consumed + dashed capacity reference; palette CVD-validated for the dark surface: `#3987e5`, `#199e70`), factory status table, production-vs-target and storage meters, alerts panel.
- Live updates: WS snapshots written straight into the query cache; 15 s polling fallback.

### Phase 3 — World Map

**Backend**
- `SimulatedWorldProvider` (`app/simulation/world.py`): static factories, power plants, train stations, drone/truck stations + resource nodes read from `database/data/resource_nodes.json`; players random-walk each tick.
- `WorldService` (`app/world/service.py`): refresh on the poll interval, live positions published on WS topic `world.players`; custom-marker persistence (`map_markers` table).
- Endpoints: `GET /api/v1/world`, `GET/POST/DELETE /api/v1/world/markers`.

**Frontend**
- Interactive Leaflet map (`src/pages/WorldMap.tsx`): CRS.Simple at 1 unit = 1 km, north up (`src/utils/mapCoords.ts`); per-type layer toggle pills, name search, hover tooltips + detail popups, live player markers streamed over WS, right-click to place custom markers (named via inline form), delete from popup. Feature colors use the validated dark categorical palette.
- Pickups: artifacts (somersloops, mercer spheres, power slugs), food/consumables, and crash-site wrecks seeded from `database/data/collectibles.json`, rendered as diamonds with `collected` state (hollow/dimmed when collected, "Hide collected" filter). Resource nodes carry `occupied` state — hollow/dashed when a miner is installed, solid when free.
- Map filters (all combinable, logic centralized in `src/utils/worldFilters.ts` with unit tests): per-type layer toggles, name search, "Hide collected", and dropdowns for **resource** (options derived from data), **purity** (impure/normal/pure), **node status** (free / miner installed), and **region** (a specific region shows only located features — nodes & pickups).

**Verified end-to-end**: pytest 24/24, vitest 16/16, production build clean, live smoke tests of world snapshot (all 9 feature types, collected/occupied counts), marker create, and a `world.players` WebSocket frame.

### Phase 4 — Factory Planner

**Backend** (`app/planner/`, `app/api/v1/plans.py`, `app/api/v1/gamedata.py`)
- Schemas (`app/schemas/planner.py`): `GridSpec`, `Placement`, `Layout`,
  `PlanSummary`, `PlanCreate/Update`, `FactoryPlan`, `PlanVersion`, `PlanExport`,
  `BuildingInfo`. Layout JSON:
  `{grid: {width, length, cell_cm}, placements: [{id, building, x, y, rotation
  (0|90|180|270), clock (0.01–2.5)}]}`.
- Models (`app/models/plan.py`): `factory_plans` (current layout + `version`) and
  append-only `plan_versions` (revert history, `ON DELETE CASCADE`).
- Pure geometry (`app/planner/geometry.py`): footprint→cells (honours `cell_cm`),
  rotation swap, rect overlap/bounds — unit-tested, no I/O.
- Service (`app/planner/service.py`): `validate_layout` collects **all**
  per-placement errors (overlap / out-of-grid / unknown building) into
  `validation_failed` details; `summarize` derives power
  (`power_mw × clock^1.321928`), machine counts, and build-cost rollup; CRUD +
  versioning + non-destructive revert + export/import.
- Game data (`app/planner/gamedata.py`): `buildings.json` + `build_costs.json`
  loaded once (`lru_cache`) and served via `GET /api/v1/gamedata/buildings` —
  one source of truth, not bundled into the frontend.
- Endpoints: `GET/POST /plans`, `GET/PUT/DELETE /plans/{id}`,
  `GET /plans/{id}/versions`, `POST /plans/{id}/revert/{version}`,
  `GET /plans/{id}/export`, `POST /plans/import`.

**Frontend** (`pages/FactoryPlanner.tsx`, route `/factory-planner`)
- Plan list sidebar (create/rename/duplicate/delete/import); SVG grid editor with
  a building palette, click-to-place, drag-to-move, rotate (R), delete (Del),
  live collision/out-of-bounds highlighting, editable grid size and per-building
  clock; summary panel (power / machine counts / build cost); version list with
  one-click revert; JSON export/import; `?` keyboard-shortcut overlay.
- `utils/plannerGrid.ts` mirrors the backend geometry (unit-tested) so the editor
  validates before saving; hooks in `hooks/usePlans.ts` + `hooks/useGameData.ts`;
  types in `types/planner.ts`; `.btn` component class added to `styles/index.css`.
- Note: Factory Planner lives at `/factory-planner`; the `/planner` route stays
  the Phase 5 **Production** Planner stub.

**Verified end-to-end**: pytest 36/36, vitest 26/26, `tsc`/production build clean,
ruff + mypy clean on new modules, live smoke test of the planner API (buildings
served, plan create with correct power summary, overlap rejection, export→import
roundtrip).

### Phase 5 — Production Planner

**Backend** (`app/production/`, `app/api/v1/production.py`, gamedata endpoints)
- Recipe/item data (`app/production/data.py`, `lru_cache`d): loads
  `recipes.json` + `alternate_recipes.json` + `items.json`; indexes producers,
  default recipe per item, raw-resource detection.
- Solver (`app/production/solver.py`): depth-first recipe-tree resolution sizing
  fractional machines per step; `recipe_overrides` (invalid → warn + fallback),
  somersloop amplification (2× output, `×4` per-machine power), cycle/depth
  guards → `warnings`. Rolls up power, per-building machine counts, raw
  materials, byproducts, and a `build_cost` shopping list (ceil machines).
- Schemas in `app/schemas/production.py`; endpoints `GET /gamedata/recipes`,
  `GET /gamedata/items`, `POST /api/v1/production/plan`. **Stateless — no tables.**

**Frontend** (`pages/Planner.tsx`, route `/planner` — replaces the stub)
- Target-item picker + rate input, per-item alternate-recipe dropdowns (only for
  items with >1 recipe in the current tree), an indented production tree with
  inline somersloop toggles, and totals panels (power, machine counts, raw
  materials/min, byproducts, build cost). Hooks in `hooks/useProduction.ts`;
  types in `types/production.ts`. `/planner` sidebar item renamed to
  "Production Planner"; `/factory-planner` stays the Phase 4 grid designer.

**Verified end-to-end**: pytest 45/45, vitest 26/26, `tsc`/build clean, ruff +
mypy clean on new modules, live smoke test of the production API (recipes/items
served, reinforced-iron-plate ×10/min solves to the correct 78 MW machine tree
with raw/cost rollups, alternate-recipe override changes the machine mix).

### Phase 6 — Logistics

**Backend** (`app/logistics/`, `app/simulation/logistics.py`, `app/api/v1/logistics.py`)
- Schemas (`app/schemas/logistics.py`): `LogisticsNode`, `LogisticsRoute` (with
  server-derived `utilization` / `over_capacity` computed fields), `TrainInfo`,
  `LogisticsSummary`, `LogisticsSnapshot`, transport tiers.
- Transport data (`app/logistics/data.py`, `lru_cache`d) from
  `transportation.json`; pure analysis (`app/logistics/analysis.py`) rolls up
  per-mode throughput, peak utilization, and over-capacity routes.
- `SimulatedLogisticsProvider` (seeded network aligned with the world map; trains
  ping-pong along the rail line) + `LogisticsService` publishing on WS topic
  `logistics.trains`; wired into `main.py` lifespan + scheduler.
- Endpoints: `GET /api/v1/logistics`, `GET /api/v1/gamedata/transport`.

**Frontend** (`pages/Logistics.tsx`, route `/trains`)
- SVG network schematic (routes colored by a green→amber→red utilization scale,
  width by throughput, live train markers streamed over WS), summary panel, and a
  routes table with utilization bars + over-capacity flags. Pure view helpers in
  `utils/logisticsView.ts` (unit-tested); WS handler in `hooks/useLogistics.ts`
  registered in `AppLayout`. Sidebar "Train Network" → "Logistics".

**Verified end-to-end**: pytest 50/50, vitest 31/31, `tsc`/build clean, ruff +
mypy clean on new modules, live smoke test of the logistics API (7 nodes / 7
routes / 2 trains, `r-plate-belt` correctly flagged over capacity at 125%, peak
utilization + per-mode throughput rollups).

### Phase 7 — Power

**Backend** (`app/power/`, `app/api/v1/power.py`, gamedata power endpoint)
- Pure analysis (`app/power/analysis.py`): headroom + status (ok/warn/critical),
  battery trend (charging/draining/stable) with projected minutes to empty/full
  from the current net draw, and rule-based recommendations.
- `build_report` (`app/power/service.py`) assembles a `PowerReport` from the live
  game-state grid stats + persisted `power_samples` history. Schemas in
  `app/schemas/power.py`. Endpoints `GET /api/v1/power`, `GET /gamedata/power`.
  **Reuses existing tables — no new schema.**

**Frontend** (`pages/Power.tsx`, route `/power`)
- Generation/consumption/headroom/battery stat tiles, the shared `PowerChart`
  history, grid-load + battery meters, and a recommendations list. Live grid
  stats patched from `dashboard.snapshot` WS frames between 15 s refetches
  (`hooks/usePower.ts`, registered in `AppLayout`); types in `types/power.ts`.

**Verified end-to-end**: pytest 55/55, vitest 31/31, `tsc`/build clean, ruff +
mypy clean on new modules, live smoke test of the power API (headroom 31%,
battery charging ~104 min to full, healthy recommendation, generator catalog).

### Phase 8 — Blueprint System

**Backend** (`app/blueprints/`, `app/api/v1/blueprints.py`, `blueprints` table)
- `Blueprint` model (`app/models/blueprint.py`): name, description, category
  (indexed), tags (JSON), favorite, reusable `data` (JSON). Registered in
  `models/__init__.py`; created via `create_all` (additions are safe).
- Service (`app/blueprints/service.py`): CRUD, client-agnostic filtering
  (category/tag/favorite/search), partial update (`exclude_unset` — favorite
  toggle), stats rollup (by category/tag, favorites), import/export. Schemas in
  `app/schemas/blueprint.py` (`BlueprintSummary` omits `data` for list views).
- Endpoints under `/api/v1/blueprints` (+ `/stats`, `/{id}/export`, `/import`).

**Frontend** (`pages/Blueprints.tsx`, route `/blueprints`)
- Search + category/tag/favorite filters, responsive card grid with favorite
  stars, create/import/export/delete, and a live stats line. Filtering, faceting,
  and stat derivation are pure and client-side (`utils/blueprintFilters.ts`,
  unit-tested); mutations in `hooks/useBlueprints.ts`; types in
  `types/blueprint.ts`.

**Verified end-to-end**: pytest 60/60, vitest 35/35, `tsc`/build clean, ruff +
mypy clean on new modules (blueprint CRUD/filter/stats/export-import covered by
tests running through the real ASGI app).

### Phase 9 — Analytics

**Backend** (`app/analytics/`, `app/api/v1/analytics.py`)
- Pure math (`app/analytics/compute.py`): `series_stats`, `uptime_fraction`,
  `compare` (recent half vs. older half) — no I/O, unit-tested.
- Service aggregates `power_samples` / `production_samples` into `PowerAnalytics`
  (produced/consumed/capacity stats, battery avg, uptime, produced-trend) and the
  busiest `ProductionAnalytics` lines. Schemas in `app/schemas/analytics.py`.
  Endpoints `GET /analytics/summary`, `GET /analytics/production/{item}`.
- **Test-infra fix**: added `SPIFFCO_SCHEDULER_ENABLED` (default true); conftest
  disables it so the periodic history job no longer races request handlers on the
  shared in-memory connection — deterministic, warning-free tests.

**Frontend** (`pages/Analytics.tsx`, route `/analytics`, new sidebar entry)
- KPI tiles (avg generation/consumption, uptime, avg battery), a generation-trend
  card, and a top-production table with per-line trend arrows. Trend formatting is
  pure (`utils/trend.ts`, unit-tested); data via `hooks/useAnalytics.ts`.

**Verified end-to-end**: pytest 66/66 (0 warnings), vitest 38/38, `tsc`/build
clean, ruff + mypy clean on new modules; analytics tests seed history through the
live session factory and assert KPIs/ranking deterministically.

### Phase 10 — AI Advisor

**Backend** (`app/advisors/`, `app/api/v1/advisor.py`)
- Pure engine (`app/advisors/engine.py`): rules over the live dashboard + logistics
  snapshots — power shortfall/headroom/battery (reuses `app/power/analysis.py`),
  unpowered machines, factory outage/underperformance, production shortage
  (<90% of target), storage backing up (≥95%), logistics over-capacity. Each
  finding has a severity, explanation, and suggested fix; ranked critical→info.
- `build_report` (`app/advisors/service.py`) adds per-severity counts. Schema in
  `app/schemas/advisor.py`; endpoint `GET /api/v1/advisor`.

**Frontend** (`pages/Advisor.tsx`, route `/advisor`, new sidebar entry)
- Findings grouped by severity with category icons, explanations, and suggested
  fixes; pure grouping in `utils/advisorView.ts` (unit-tested); `hooks/useAdvisor.ts`.

**Verified end-to-end**: pytest 70/70, vitest 40/40, `tsc`/build clean, ruff +
mypy clean on new modules, live smoke of the advisor API (simulated state yields
the over-capacity `Iron Plate Overflow` belt + `3 machines unpowered` warnings).

### Phase 11 — FRM Integration

**Backend** (`app/connectors/frm/`)
- `FrmClient` (`client.py`): async httpx client with timeout + short-TTL per-path
  cache + health probe; injectable transport for tests.
- Pure normalizers (`normalize.py`): raw FRM payloads → dashboard/world/logistics
  schemas, defensive (`.get` fallbacks). Raw FRM shapes never leave the package.
- `FrmConnector` (`connector.py`): probes once on `start()` (raises if unreachable),
  then polls in the background, caching the latest normalized snapshots; publishes
  `frm.status`. FRM-backed providers (`providers.py`) satisfy the sync `snapshot()`
  protocols so services run unchanged.
- Wired in `main.py`: `SPIFFCO_FRM_ENABLED` selects FRM vs. simulation, with
  **fallback to simulation** when FRM is unreachable; `/health` reports the real
  FRM state. New settings: `frm_enabled`, `frm_cache_ttl_seconds` (+ existing).

**Frontend**: none needed — the top-bar FRM badge already reads `health.frm`.

**Verified end-to-end**: pytest 76/76, ruff + mypy clean on new modules; FRM tests
drive normalization/caching/polling via a fake httpx transport, and a live smoke
confirms FRM-enabled-but-unreachable boots on simulation (`health.frm =
not_configured`, `dashboard.source = simulation`). Full live validation needs a
running mod (see `docs/KNOWN_LIMITATIONS.md`).

### Phase 12 — Offline Mode (final spec phase)

**Backend** (`app/offline/`, `app/api/v1/offline.py`)
- Pure save parser (`save_parser.py`): parses the `.sav` header (session name,
  map, build version, play duration, save timestamp) and inflates the compressed
  body by scanning for zlib streams (version-robust); counts buildings from actor
  instance names (`Build_..._C_<id>`). Raises `SaveParseError` on non-saves.
- Building catalog (`building_map.py`): `Build_..._C` → display name / category /
  nominal power. `SaveDataSource` + `SaveGame/World/LogisticsProvider`
  (`provider.py`) reshape the parse into the existing schemas via the FRM
  normalizers with `source="save"`. `OfflineManager` (`manager.py`) swaps every
  service between the base source and a loaded save, restoring it on clear.
- Endpoints: `GET /api/v1/offline/status`, `POST /api/v1/offline/save` (multipart,
  `SPIFFCO_SAVE_MAX_UPLOAD_MB`-limited), `DELETE /api/v1/offline/save`. Schemas in
  `app/schemas/offline.py`. `use_provider` added to World/Logistics services.

**Frontend** (`pages/Offline.tsx`, route `/offline`, new sidebar entry)
- Save upload + parsed session summary (machines, generators, estimated power,
  per-building table) and a "return to live data" action. Hooks in
  `hooks/useOffline.ts` (upload invalidates all server-state queries); types in
  `types/offline.ts`. A data-source badge in the top bar shows
  simulation / live game / save file globally.

**Verified end-to-end**: pytest 82/82, vitest 40/40, `tsc`/build clean, ruff +
mypy clean on new modules, live lifespan smoke (upload a synthetic save →
dashboard `source` flips to `save` with correct machine/power rollups → clear
restores simulation).

**Limits**: positions/inventories are not extracted, so power figures are
estimates and the World Map / Logistics pages are not populated from saves (see
`docs/KNOWN_LIMITATIONS.md`).

## 🚧 Incomplete

The Factories (`pages/Factories.tsx`) and Resources (`pages/Resources.tsx`)
pages are now built, rendering off the existing dashboard and world snapshots
respectively (no dedicated backend packages needed). The `stubs.tsx`
placeholder module has been removed.

### Known gaps in shipped code

- **FRM connection is configurable in-app** — Settings page (or `PUT /api/v1/settings/frm`) enables/points the FRM connector at runtime, persisted in `app_settings` and applied without a restart; falls back to `SimulatedGameProvider` when no FRM mod is reachable. Env vars `SPIFFCO_FRM_ENABLED` / `SPIFFCO_FRM_BASE_URL` set the initial default.
- **Auth settings exist but are not enforced** — do not expose beyond localhost until the auth middleware lands.
- **Seed game data is a small subset** — full import from the game's `Docs.json` via a planned `scripts/import_game_data.py`.
- **Frontend types mirrored by hand** — generate from OpenAPI before the contract grows.
- **No E2E tests** — Playwright suite planned in `tests/` now that real UI exists.
- **Frontend bundle >500 kB** (Recharts in the main chunk) — code-split when more chart pages exist.
- **Dashboard chart and world map not yet visually inspected in a browser** (verified via API/tests only).
- **Map has no terrain background tiles** — features render on a plain dark canvas with a world-bounds outline; licensed map tiles/imagery are a follow-up for Phase 3 polish.
- **Planner runs on static seed game data** — only 9 buildings in `buildings.json` and a partial `build_costs.json`; the full set arrives with the planned `scripts/import_game_data.py`.
- **No terrain/blueprint background under the planner grid** — layouts are placed on a plain grid; area planning against real map regions is a later polish.
- **Still no Alembic migrations** — the Phase 4 `factory_plans` / `plan_versions` tables were added via `create_all`; Alembic remains the next-schema-change prerequisite.
- Cross-cutting backlog also tracked in [docs/ROADMAP.md](docs/ROADMAP.md): plugin runtime, history retention/pruning policy.

## ▶ Next session — detailed plan

### All 12 spec phases are complete.

The remaining work is the post-spec hardening backlog below plus the offline
parser's follow-up (per-actor transform parsing to populate the map/logistics
from saves and replace estimated power with recipe/clock-derived figures).

### Hardening backlog (post-spec)

- **Alembic bootstrap** (overdue — `factory_plans`, `plan_versions`, `blueprints`).
- **Validate FRM normalization** against a live mod; capture fixtures.
- **OpenAPI-generated frontend types**; **code-split** the >830 kB bundle.
- **History retention/pruning** job; **auth enforcement** middleware; **E2E** tests.
- **Visual browser pass** over every page (never yet eyeballed in a browser).

### Housekeeping (small, high value — carried forward)

- **Visual check**: open the app (`scripts/dev.ps1`) and eyeball the two new
  planners (Factory Planner drag/rotate/collision; Production Planner tree +
  totals), plus the still-unverified Dashboard chart and World Map.
- **eslint isn't installed** in the current env (`npm run lint` fails on a
  missing binary) — `npm install` to restore the devDependency, then lint.
- **Alembic bootstrap** is overdue: Phases 4 and 8 added tables via `create_all`.
- **OpenAPI-generated frontend types** — the API surface keeps growing; generate
  before it grows further.
- **Bundle >830 kB** — code-split (Recharts/Leaflet) is increasingly worthwhile.
- **History grows unbounded** — `power_samples` / `production_samples` never
  prune; the Analytics phase makes a retention job more valuable.

### Design decisions already made (don't re-litigate)

- Simulated providers stay until Phase 11; anything new must go through a provider interface (`GameStateProvider`, `WorldProvider` pattern).
- Raw FRM/save data never crosses the API boundary; everything is normalized in `app/schemas/`.
- Realtime = EventBus → `/ws` topics (catalog in `shared/constants/ws_topics.json`); never push to sockets directly.
- Colors: dark categorical palette from the dataviz skill (`#3987e5` blue, `#199e70` aqua, `#c98500` yellow, `#9085e9` violet, `#d55181` magenta, `#d95926` orange, `#008300` green, `#e66767` red); infrastructure = circles, pickups = diamonds; hollow/dimmed = consumed/claimed.
- react-leaflet is pinned to v4 (v5 requires React 19).
- Errors: raise `AppError` subclasses; standard envelope; routers stay thin.

### Backlog (unchanged, ordered by leverage)

1. Minimal FRM read path (may pull forward into any phase once a live game is available for testing).
2. OpenAPI-generated frontend types (the Phase 4 surface is large; do before Phase 5 grows it further).
3. Auth enforcement middleware.
4. Full game-data import script (`scripts/import_game_data.py` from the game's Docs.json).
5. E2E Playwright suite in `tests/`.
6. History retention/pruning job (power/production samples grow unbounded).
7. Map terrain tiles (licensed art needed) and marker clustering at low zoom.

## How to run

```bash
scripts/dev.ps1              # Windows: starts backend (:8000) + frontend (:5173)
cd backend && pytest         # backend tests
cd frontend && npm test      # frontend tests
docker compose up --build    # self-hosted deployment
```
