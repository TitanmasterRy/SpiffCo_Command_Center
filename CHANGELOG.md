# Changelog

All notable changes to SpiffCo Command Center are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the
project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added — Phase 8: Blueprint System

- Persisted blueprint library (`blueprints` table): name, description, category,
  tags, favorite, and a reusable `data` payload (layout/recipe fragment).
- CRUD + filtering (category / tag / favorite / name-description search),
  favorite toggling, per-blueprint import/export, and a library stats rollup
  (`app/blueprints/service.py`, schemas in `app/schemas/blueprint.py`); endpoints
  under `/api/v1/blueprints` (+ `/stats`, `/{id}/export`, `/import`).
- Blueprints page (`pages/Blueprints.tsx`, route `/blueprints`): search + category/
  tag/favorite filters, a responsive card grid with favorite stars, create/
  import/export/delete, and a live stats line. Filtering/faceting/stat derivation
  are pure and client-side (`utils/blueprintFilters.ts`, unit-tested).

### Added — Phase 7: Power

- Power analysis (`app/power/analysis.py`, pure): grid headroom + status
  (ok/warn/critical), battery trend (charging/draining/stable) with projected
  minutes to empty/full from the current net draw, and rule-based
  recommendations (a Phase 10 advisor precursor).
- `PowerReport` assembled from the live game-state grid stats plus the persisted
  `power_samples` history; endpoints `GET /api/v1/power` and
  `GET /api/v1/gamedata/power` (generator catalog from `power_buildings.json`).
- Power page (`pages/Power.tsx`, route `/power`): generation/consumption/headroom/
  battery stat tiles, the shared power-history chart, grid-load + battery meters,
  and a recommendations list; live grid stats patched from `dashboard.snapshot`
  WS frames between 15 s refetches.

### Added — Phase 6: Logistics

- Logistics network model (`app/schemas/logistics.py`): nodes (stations/
  factories/ports) joined by directed routes carrying an item at a throughput;
  each route's `utilization` and `over_capacity` are derived server-side against
  its belt/pipe/vehicle tier capacity.
- `SimulatedLogisticsProvider` + `LogisticsService`: a seeded mid-game network
  with trains ping-ponging along the rail line, published live on WS topic
  `logistics.trains`; pure throughput analysis (`app/logistics/analysis.py`)
  rolls up per-mode throughput, peak utilization, and over-capacity routes.
- Endpoints: `GET /api/v1/logistics` (network + trains + summary) and
  `GET /api/v1/gamedata/transport` (belt/pipe tiers + vehicles).
- Logistics page (`pages/Logistics.tsx`, route `/trains`): an SVG network
  schematic (routes colored by a green→amber→red utilization scale, width by
  throughput, live train markers streamed over WS), a summary panel, and a
  routes table with utilization bars and over-capacity flags. Pure view helpers
  in `utils/logisticsView.ts` (unit-tested).

### Added — Phase 5: Production Planner

- Recipe-tree solver (`app/production/solver.py`): resolves a target item + rate
  into a full production chain, sizing fractional machines per step down to raw
  resources; power draw, per-building machine counts, raw-material demand,
  byproducts, and a construction shopping list roll up across the tree.
- Alternate-recipe selection via `recipe_overrides` (invalid overrides warn and
  fall back to the default recipe); somersloop amplification doubles a node's
  output for a super-linear (`×4` per machine) power cost; recipe cycles and
  unknown machines surface as `warnings` rather than failing.
- Recipe/item game data (`app/production/data.py`, `lru_cache`d) served via
  `GET /api/v1/gamedata/recipes` and `/gamedata/items`; solve endpoint
  `POST /api/v1/production/plan`.
- Production Planner page (`pages/Planner.tsx`, route `/planner`): target picker,
  rate input, per-item alternate-recipe dropdowns, an indented production tree
  with inline somersloop toggles, and totals panels (power, machines, raw
  materials, byproducts, build cost).

### Added — Phase 4: Factory Planner

- Persisted factory plans with append-only version history: `factory_plans` and
  `plan_versions` tables; every layout save records a new revertible version.
- Planner service (`app/planner/`): pure grid geometry (footprints, rotation,
  overlap, bounds), full layout validation that reports **all** offending
  placements at once (`validation_failed` with per-placement details), and a
  derived summary (power draw `power_mw × clock^1.321928`, machine counts,
  build-cost rollup — the seed for the Phase 5 shopping list).
- REST API: `GET/POST /api/v1/plans`, `GET/PUT/DELETE /api/v1/plans/{id}`,
  `GET /api/v1/plans/{id}/versions`, `POST /api/v1/plans/{id}/revert/{version}`,
  `GET /api/v1/plans/{id}/export`, `POST /api/v1/plans/import`.
- `GET /api/v1/gamedata/buildings`: buildings + footprints + build costs served
  from `database/data/` (one source of truth; `lru_cache`d) instead of bundling
  JSON into the frontend.
- Factory Planner page (`pages/FactoryPlanner.tsx`): plan list sidebar
  (create/rename/duplicate/delete/import), SVG grid editor with a building
  palette, click-to-place, drag-to-move, rotate (R), delete (Del), live
  collision/out-of-bounds highlighting, editable grid size and per-building
  clock, live power/cost/machine summary, version list with one-click revert,
  JSON export/import, and a `?` keyboard-shortcut overlay.
- Grid math mirrored client-side in `utils/plannerGrid.ts` (unit-tested) so the
  editor validates before saving.

### Added — Phase 3: World Map (pickups & node states)

- Pickup features on the map: **artifacts** (somersloops, mercer spheres, power
  slugs), **food & consumables** (paleberry, beryl nut, bacon agaric), and
  **crash sites/wrecks**, seeded from `database/data/collectibles.json`.
- Per-pickup `collected` state and per-node `occupied` state (miner installed)
  on `MapFeature`; simulated save marks ~40% of pickups collected and the
  starter iron/limestone nodes occupied.
- Map filters: resource, purity, node status (free / miner installed), and
  region dropdowns; filter logic centralized in `utils/worldFilters.ts` with
  unit tests.
- Map rendering: pickups draw as diamonds (infrastructure stays circles);
  collected pickups and occupied nodes render hollow/dimmed (occupied nodes
  dashed), with state noted in tooltips/popups; new layer toggles for the three
  pickup categories and a "Hide collected" filter.

### Added — Phase 3: World Map

- `SimulatedWorldProvider`: static features (factories, power plants, train
  stations, drone ports, truck stations; resource nodes loaded from
  `database/data/resource_nodes.json`) plus wandering players.
- `WorldService` publishing live positions on WS topic `world.players`.
- Persisted custom markers (`map_markers` table) with
  `GET/POST/DELETE /api/v1/world/markers`; `GET /api/v1/world` snapshot.
- Interactive Leaflet map (CRS.Simple, km scale, north up): per-type layer
  toggles, name search, hover tooltips + popups, live player markers streamed
  over WebSocket, right-click to add custom markers, delete from popup.

### Added — Phase 2: Dashboard

- Pluggable `GameStateProvider` with a `SimulatedGameProvider` (random-walk
  mid-game telemetry) until the FRM connector lands in Phase 11.
- `GameStateService`: periodic refresh (poll interval setting), snapshot
  publishing on WS topic `dashboard.snapshot`, 30s history sampling.
- History tables `power_samples` / `production_samples` and endpoints
  `GET /api/v1/dashboard`, `/dashboard/history/power`,
  `/dashboard/history/production/{item}`.
- Rule-based alerts (battery low, power headroom, factory efficiency,
  storage full) — precursor to the Phase 10 advisor.
- Dashboard UI: stat tiles (power, battery, machines, efficiency), live power
  history chart (Recharts, CVD-validated palette), factory status table,
  production/storage meters, alert list; snapshots stream in over WebSocket
  with polling fallback.

### Added — Phase 1: Foundation

- FastAPI backend with application factory, versioned API (`/api/v1`), and OpenAPI docs.
- Typed configuration via `pydantic-settings` (`SPIFFCO_` env prefix, `.env` support).
- Structured logging (console + optional rotating file handler).
- Centralized error handling with a consistent JSON error envelope.
- SQLite database layer (SQLAlchemy 2.0, async engine) with automatic schema creation.
- WebSocket server (`/ws`) with topic-based subscriptions backed by an internal event bus.
- Background task scheduler for periodic jobs (asyncio-based, no external broker).
- FRM connector package scaffold (implemented in Phase 11).
- React 18 + TypeScript + Vite + TailwindCSS frontend shell: routing, layout,
  page stubs for all planned modules, API/WebSocket clients, Zustand connection store.
- Static game-data JSON files (items, recipes, buildings, resources, …).
- Full documentation set (architecture, API reference, guides, roadmap).
- Docker Compose setup for one-command self-hosting.
- Unit tests for backend foundation (config, health, event bus, scheduler, WS).
