# Project State

Last updated: **2026-07-13** · Current milestone: **Phase 8 complete, Phase 9 next**

Snapshot of what exists and works versus what remains. Companion docs:
[docs/ROADMAP.md](docs/ROADMAP.md) (phase plan) and
[docs/KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md) (deliberate gaps).

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

## 🚧 Incomplete

### Phases not started

| Phase | Scope |
|---|---|
| 9 — Analytics | Historical graphs, uptime, comparisons, KPIs |
| 10 — AI Advisor | Bottleneck/shortage/starvation detection with explained recommendations |
| 11 — FRM Integration | Real connector: discovery, reconnect, health, caching, WS + polling fallback, normalization |
| 12 — Offline Mode | Save-file parsing, planning without a live game |

The Factories and Resources pages exist only as placeholder stubs
(`frontend/src/pages/stubs.tsx`); their backend packages are empty scaffolds.
(Much of their content is already covered elsewhere: per-factory status on the
Dashboard, resource nodes on the World Map.)

### Known gaps in shipped code

- **Dashboard runs on simulated data** — `SimulatedGameProvider` until Phase 11 swaps in the FRM provider (interface already matches).
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

### Primary goal: Phase 9 — Analytics

Historical graphs, uptime, production/power history, comparisons, and KPIs. Most
of the raw data already exists: `power_samples` and `production_samples` are
sampled every 30 s (`GameStateService.record_history`), with `/dashboard/history`
endpoints. Phase 9 turns that into an analytics surface. Suggested order:

1. **Analytics service** (`app/analytics/` — package scaffold exists):
   - Aggregations over the history tables: min/max/avg power and production,
     uptime (% of samples above a threshold), and time-window comparisons
     (e.g. last hour vs. previous). Normalize into `app/schemas/analytics.py`.
   - Endpoints like `GET /api/v1/analytics/summary` and
     `/analytics/production/{item}`; reuse the existing sample queries.
   - Watch the unbounded-history gap (samples grow forever) — consider the
     retention/pruning job from the backlog while here.
2. **Frontend**: a new Analytics page (or wire the `/factories`/`/resources`
   stubs) — KPI tiles, multi-series history charts (reuse Recharts + the dataviz
   palette), and a comparison view.
3. **Tests**: aggregation/uptime/comparison math (backend); KPI/format helpers
   (frontend unit tests).

### Housekeeping (small, high value — carried forward)

- **Visual check**: open the app (`scripts/dev.ps1`) and eyeball the two new
  planners (Factory Planner drag/rotate/collision; Production Planner tree +
  totals), plus the still-unverified Dashboard chart and World Map.
- **eslint isn't installed** in the current env (`npm run lint` fails on a
  missing binary) — `npm install` to restore the devDependency, then lint.
- **Alembic bootstrap** is overdue: Phase 4 added two tables via `create_all`.
- **Fix pytest warnings** (SAWarning about the `ProductionSample` identity map
  during history sampling — pre-existing, worth silencing at the source).
- **OpenAPI-generated frontend types** — the API surface keeps growing; generate
  before Phase 6 adds more.
- **Bundle >800 kB** — code-split (Recharts/Leaflet) is increasingly worthwhile.

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
