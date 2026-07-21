# Changelog

All notable changes to SpiffCo Command Center are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the
project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added — World Map: pin ring colored by the building's paint swatch

- Miners and oil/water/well extractors now appear on the map (from FRM's
  `getExtractor` feed, previously unfetched) as building markers. Each painted
  building's pin **ring, anchor line, and position dot are colored to its in-game
  paint swatch** (its primary customization color), so a color-coded factory
  reads the same on the map.
- Backend: `normalize.py` reads the swatch from the building payload
  (`ColorSlot.PrimaryColor` / `PrimaryColor` / `Color`, accepting hex strings,
  `{R,G,B}` objects of 0–1 floats or 0–255 ints, and `[r,g,b]` lists) into
  `meta.color`; unpainted buildings omit it and fall back to the per-type color.
  The simulated provider paints a few sample factories/extractors so the feature
  is visible without a live game.
- Frontend: `swatchColor()` in `utils/mapIcons.ts` validates `meta.color` and,
  when present, uses it for the pin's outside (ring) color.

### Added — User accounts: login, account approval, and per-user permissions

- **Login for the whole site.** New `users` table with account status
  (`pending` / `active` / `disabled`), a role label, and an explicit permission
  list. Auth is opt-in via `SPIFFCO_AUTH_ENABLED` (default off, preserving the
  single-user LAN experience); when on, every `/api/v1` data endpoint requires a
  valid session and the WebSocket stream requires a `?token=` handshake.
- **Self-service sign-up → admin approval.** `POST /auth/register` creates a
  pending account; it cannot log in until an admin approves it. `POST /auth/login`
  issues a stateless HMAC session token (same scheme as the admin panel, no new
  deps); `GET /auth/me` restores a session. Public sign-up can be disabled with
  `SPIFFCO_AUTH_ALLOW_REGISTRATION=false`.
- **Per-user permissions.** A permission catalog gates each page (`view:*`) plus
  privileged actions (`use:admin-cheats`, `manage:users`); role presets
  (viewer / operator / admin) seed the checkboxes, which the admin can then
  customize per account. Backend enforces action permissions; the frontend nav
  and routes gate page visibility.
- **Admin → Accounts tab.** The admin page now has *Cheats* and *Accounts* tabs.
  Accounts lists pending requests (Approve / Reject) and existing users with a
  role selector, permission checkboxes, enable/disable, and delete. Endpoints
  live under `/api/v1/admin/users` (require `manage:users`).
- **Owner account** is seeded/refreshed from `SPIFFCO_ADMIN_PASSWORD`
  (or `_HASH`) on startup — always active with full access, and protected from
  disabling or deletion — so there is always an approver. The former
  `/admin/login` endpoint is replaced by the unified `/auth/*` flow; the cheat
  panel now requires the `use:admin-cheats` permission.
- Frontend: `authStore` (localStorage-backed session), a login/request-account
  screen, `RequireAuth` / `RequirePermission` route guards, a permission-filtered
  sidebar, and a top-bar user menu with sign-out.

### Added — Admin Panel: player targeting, shared-state flags, achievement safety

- Catalog actions now carry `scope` and `affects_all`. Player-scoped cheats
  (inventory, equipment, movement, per-player visual overlays, build-gun rule
  toggles) get a "Target player" selector in the panel, fed by the live
  online-player list from the world snapshot; the choice is sent as
  `params.player` and audit-logged. The bridge resolves the name
  case-insensitively and fails (never retargets) if that player is offline;
  empty = first connected player.
- Cheats that alter session-shared state (unlocks, mass build/delete, power,
  logistics, trains, drones, world, creatures, radiation, painting) are badged
  **All players** in the UI.
- Achievement safety: the bridge only uses cheat-manager/engine calls and never
  enables Advanced Game Settings / creative (which permanently disables
  achievements). AGS-only actions (`build.free_placement`, `build.no_collision`,
  `build.no_clearance`) are hard-refused with an explanatory message; the
  policy is documented in the bridge README and noted in the panel UI.

### Added — SpiffCoBridge companion mod (scaffold) + authenticated dispatch

- `bridge-mod/SpiffCoBridge/`: an SML (Satisfactory Mod Loader) UE plugin that
  runs an authenticated HTTP server in-game (`GET /health`, `POST /execute`)
  and executes admin-panel actions via a command registry keyed by the same
  action ids as the backend catalog. Wave 1 implements fly / noclip / god mode,
  item spawning (class-name, display-name, or asset-path resolution), clear
  inventory, unlock all recipes / MAM, teleport, time-of-day + freeze /
  multiplier, and kill-all-creatures; everything else returns 501 so the panel
  reports it honestly. Server-authority only (never listens on clients);
  config via `[/Script/SpiffCoBridge.SpiffCoBridgeSettings]` in `Game.ini`
  (`bEnabled`, `Port` default 8091, `AuthToken`). Compiles inside the SML
  project (see its README); `ADJUST-ME` markers flag the FactoryGame call
  sites most likely to need signature touch-ups per game update.
- Backend: `SPIFFCO_ADMIN_COMMAND_TOKEN` — the command executor now sends a
  shared secret as `X-SpiffCo-Token`, matching the bridge's `AuthToken`.
- `scripts/mock_bridge.py`: stdlib mock implementing the bridge contract so the
  real-dispatch path can be tested without the game (`--port`, `--token`).

### Added — Admin Panel (Phase 13)

- Password-protected admin panel at `/admin` with a full cheat catalog: player
  (inventory / equipment / movement), building (placement / mass building /
  delete tools), power, logistics, trains, drones, world, creatures, radiation,
  factory analysis highlights, building inspector, and appearance — ~170 actions
  rendered generically from a data-driven catalog (`backend/app/admin/catalog.py`).
- Auth: `POST /api/v1/admin/login` exchanges the configured credentials
  (`SPIFFCO_ADMIN_USERNAME` + `SPIFFCO_ADMIN_PASSWORD` or
  `SPIFFCO_ADMIN_PASSWORD_HASH`, PBKDF2) for a stateless HMAC-signed session
  token; every other `/api/v1/admin/*` endpoint requires it. Login fails closed
  when no password is configured — there is no default credential.
- Dispatch is pluggable (`SPIFFCO_ADMIN_COMMAND_URL`): with a game-side command
  endpoint configured (companion mod / server bridge, `POST /execute`), actions
  execute for real; without one they are acknowledged locally as `simulated`.
  FRM is read-only telemetry and cannot execute commands.
- Server-tracked toggle state, an audit log of every command (`GET
  /api/v1/admin/log`), `admin.cheat` events on the bus, and saved presets
  (teleport locations, inventory presets) persisted via `app_settings`.

### Changed — World Map: Ctrl-gated zoom + performance

- Wheel zoom now requires holding **Ctrl** (or ⌘): a plain scroll pages past the
  map instead of trapping the wheel, and Ctrl+scroll zooms toward the cursor in
  the map's 0.25 steps (throttled so a trackpad pinch can't rocket across the
  range). A brief "Hold Ctrl and scroll to zoom" hint appears on a modifier-less
  scroll. Leaflet's native `scrollWheelZoom` is off; a small `CtrlWheelZoom`
  handler drives it.
- Performance: the map no longer lags with thousands of markers. The cursor
  coordinate readout is self-contained so mouse movement re-renders only that
  box (previously every `mousemove` rebuilt every marker). The feature and
  static-pin layers are memoized and **viewport-culled** — only markers near the
  visible bounds are mounted (e.g. ~20–800 in view instead of ~6,000+), the way
  SCIM's map only draws what's on screen.

### Fixed — World Map: marker icons hidden behind the pin disc

- Marker icon overlays now paint above the pin's head circle. Leaflet's
  stylesheet gives inline SVGs `z-index: 200`, so the colored disc was covering
  the icon `<img>` (which had `z-index: auto`) and every marker read as a plain
  colored circle. The icon image and glyph fallback now set `z-index: 400`
  (`utils/mapIcons.ts`). Also floored the icon to a legible 16px minimum so it
  no longer shrinks to an indistinct dot at low zoom.

### Changed — World Map: SCIM-inspired navigation feel

- Studied the SC-InteractiveMap source (educational only — its license forbids
  code/asset reuse, so everything is reimplemented) and adopted its map-feel
  parameters: fractional zoom in 0.25 steps (`zoomSnap`/`zoomDelta`), a wider
  zoom range (−1.5 to 8) for close-up inspection, soft pan bounds so the view
  can't wander into the void, and canvas rendering for path layers.
- Marker icons now scale with zoom level (`iconScale` in `utils/mapIcons.ts`):
  smaller when the whole map is visible, larger up close.
- The map view (center + zoom) persists in localStorage across visits, and the
  map now fills the page height instead of a fixed 70vh/32rem box.
- Leaflet tooltips/popups are dark-themed to match the app.

### Added — External Tools embeds

- New "External Tools" sidebar section embedding community planners in-app
  (`src/pages/ExternalTool.tsx`, routes under `/tools/*`): the
  satisfactory-calculator.com Production and Power planners, the
  satisfactorytools.com production planner, and the SCIM interactive map
  (save-file based; the World Map page remains the live-feed map). Each embed
  has reload and open-in-new-tab controls; embedded apps keep their own state
  inside the frame.

### Added — Deployment: single-image Fly.io target

- The FastAPI app can now serve the built SPA from the same origin
  (`app.main.mount_frontend`, gated by `SPIFFCO_STATIC_DIR`): hashed assets are
  served directly and non-API paths fall back to `index.html` for client-side
  routing. No-op in dev, where Vite serves the frontend separately.
- Root `Dockerfile` (multi-stage: build frontend → serve from backend) plus
  `fly.toml` and `.dockerignore` for a one-command free public deploy on Fly.io
  (simulation + offline data; SQLite on a persistent volume). See
  `docs/DEPLOYMENT.md`.

### Added — Phase 12: Offline Mode (final spec phase)

- Save-file parser (`app/offline/save_parser.py`, pure/no-I/O): reads the `.sav`
  header exactly (session name, map, build version, play time, save timestamp)
  and inflates the compressed body by scanning for its zlib streams — robust
  across save-format versions. Buildings are counted by matching actor instance
  names (`Build_..._C_<id>`), enough to drive machine counts and a power estimate
  without the fragile full property deserialization.
- `SaveDataSource` + three providers (`app/offline/provider.py`) reshape a parsed
  save into the existing dashboard/world/logistics schemas — reusing the FRM
  normalizers with a new `source="save"` — so the services run unchanged. An
  `OfflineManager` swaps every service between the base source (simulation/FRM)
  and a loaded save at runtime, and restores it on clear.
- Endpoints under `/api/v1/offline`: `GET /status`, `POST /save` (multipart
  upload, size-limited via `SPIFFCO_SAVE_MAX_UPLOAD_MB`), `DELETE /save`.
- Building-class catalog (`app/offline/building_map.py`) maps `Build_..._C`
  classes to display names, categories, and nominal power.
- Frontend **Offline Mode** page (`/offline`): upload a `.sav`, see the parsed
  session summary (machines, generators, estimated power, per-building table),
  and return to live data. A data-source badge in the top bar shows
  simulation / live game / save file globally.
- Limits (see KNOWN_LIMITATIONS): positions and inventories are not extracted, so
  power figures are estimates and the World Map / Logistics pages are not
  populated from saves.

### Added — Phase 11: FRM Integration

- Real Ficsit Remote Monitoring connector (`app/connectors/frm/`): an async HTTP
  client with a timeout and short-TTL per-path cache (`client.py`), pure
  normalizers mapping raw FRM payloads into the internal dashboard/world/logistics
  schemas (`normalize.py`), and a background-polling `FrmConnector` that holds the
  latest normalized snapshots and publishes connection-state changes on
  `frm.status`.
- FRM-backed providers (`providers.py`) satisfy the existing `snapshot()`
  protocols, so the services run unchanged on live data. Selected at startup via
  `SPIFFCO_FRM_ENABLED`; **falls back to the simulated providers** when FRM is
  unreachable, so the app always boots. `/health` now reports the real FRM
  connection state (`connected`/`disconnected`/`not_configured`).
- Raw FRM shapes never leave the connector package. Field mapping is defensive
  and based on the FRM API; it needs validation against a live mod (see
  KNOWN_LIMITATIONS). Tested end-to-end with a fake HTTP transport — no game
  required.

### Added — Phase 10: AI Advisor

- Rule-based advisor engine (`app/advisors/engine.py`, pure) that derives ranked,
  explained findings from the live snapshots: power shortfall / low headroom /
  draining battery, unpowered machines, factory outages/underperformance,
  production shortages, storage backing up, and logistics over-capacity. Each
  finding carries a severity, a plain-language explanation, and a suggested fix.
- `GET /api/v1/advisor` returns the ranked `AdvisorReport` (findings +
  per-severity counts), assembled from the game-state and logistics services.
- Advisor page (`pages/Advisor.tsx`, route `/advisor`, new sidebar entry):
  findings grouped by severity with category icons, explanations, and suggested
  fixes; severity grouping is pure (`utils/advisorView.ts`, unit-tested).

### Added — Phase 9: Analytics

- Pure analytics math (`app/analytics/compute.py`): series statistics
  (min/max/avg/latest), an uptime fraction (samples with generation ≥ demand),
  and a recent-vs-previous window comparison.
- Analytics service aggregating the `power_samples` / `production_samples`
  history into power KPIs and the busiest production lines; endpoints
  `GET /api/v1/analytics/summary` and `/analytics/production/{item}`.
- Analytics page (`pages/Analytics.tsx`, route `/analytics`, new sidebar entry):
  KPI tiles (avg generation/consumption, uptime, avg battery), a generation-trend
  card, and a top-production table with per-line trend arrows. Trend formatting is
  pure (`utils/trend.ts`, unit-tested).

### Changed

- Added `SPIFFCO_SCHEDULER_ENABLED` (default true) to disable the periodic
  scheduler; tests now run with it off, so background history writes no longer
  race request handlers on the shared in-memory connection — removing pre-existing
  intermittent failures and the `ProductionSample` identity-map warnings.

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
