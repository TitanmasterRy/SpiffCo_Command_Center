# API Reference

Interactive documentation is always available at `http://<host>:8000/docs`
(OpenAPI/Swagger) — this file summarizes the contract and its conventions.

## Conventions

- Base path: `/api/v1`
- All responses are JSON. Errors always use the envelope:

```json
{ "error": { "code": "not_found", "message": "…", "details": {} } }
```

| Code | HTTP | Meaning |
|---|---|---|
| `validation_failed` | 422 | Bad input |
| `not_found` | 404 | Missing resource |
| `conflict` | 409 | State conflict |
| `unauthorized` | 401 | Auth required/invalid |
| `upstream_unavailable` | 503 | FRM unreachable |
| `internal_error` | 500 | Unexpected failure |

## Endpoints (Phase 1)

### `GET /api/v1/health`

Backend health. Response: `HealthStatus`

```json
{
  "status": "ok",
  "version": "0.1.0",
  "environment": "development",
  "database": "ok",
  "frm": "not_configured",
  "uptime_seconds": 123.4,
  "server_time": "2026-07-12T12:00:00Z"
}
```

### `GET /api/v1/info`

App metadata: `{ "name", "version", "environment" }`.

### `GET /api/v1/settings` · `GET/PUT /api/v1/settings/{key}`

Persisted user settings. `PUT` body: `{ "key": "<any>", "value": <json> }` —
the path key is authoritative. `GET` of a missing key returns 404.

## Endpoints (Phase 2)

### `GET /api/v1/dashboard`

Latest `DashboardSnapshot` (`power`, `machines`, `factories`, `production`,
`storage`, `alerts`; `source` is `"simulation"` until FRM lands). 503
`upstream_unavailable` until the first refresh completes. The same payload is
pushed on WS topic `dashboard.snapshot` every poll interval (default 5 s).

### `GET /api/v1/dashboard/history/power?limit=120`

Recent power samples (30 s cadence), oldest first:
`{timestamp, produced_mw, consumed_mw, capacity_mw, battery_percent}`.

### `GET /api/v1/dashboard/history/production/{item}?limit=120`

Recent production-rate samples for one item, oldest first.

## Endpoints (Phase 3)

### `GET /api/v1/world`

`WorldSnapshot`: `players` (live positions, also streamed on WS topic
`world.players`) and `features` (factories, resource nodes, power plants,
train stations, drone ports, truck stations, artifacts, collectibles/food,
wrecks) with game-world positions in cm. State flags: pickups carry
`collected: bool`, resource nodes carry `occupied: bool` (extractor
installed); both are `null` for other feature types.

### `GET/POST /api/v1/world/markers` · `DELETE /api/v1/world/markers/{id}`

Custom marker CRUD. POST body:
`{name, position: {x,y,z}, icon?, color? (#rrggbb), notes?}` → 201 with `id`.

## Endpoints (Phase 4 — Factory Planner)

### `GET /api/v1/gamedata/buildings`

`BuildingInfo[]`: `{id, name, category, power_mw, inputs, outputs,
footprint: {width, length}, build_cost: {<item-id>: qty}}`. Static, cached.

### `GET /api/v1/plans` · `POST /api/v1/plans`

List returns `PlanSummaryInfo[]` (no layout bodies), newest first. POST body
`PlanCreate` `{name, description?, layout?}` → 201 `FactoryPlan`
(`…, version, layout, summary`). A `layout` is
`{grid: {width, length, cell_cm}, placements: [{id, building, x, y, rotation
(0|90|180|270), clock (0.01–2.5)}]}`. Invalid layouts return `422
validation_failed` with `details.placements` mapping each offending placement id
to its problems (overlap, out-of-grid, unknown building).

### `GET/PUT/DELETE /api/v1/plans/{id}`

GET → full `FactoryPlan`. PUT body `PlanUpdate` `{name?, description?, layout?,
comment?}`; supplying a `layout` appends a new version. DELETE → 204.

### `GET /api/v1/plans/{id}/versions` · `POST /api/v1/plans/{id}/revert/{version}`

Version history (`PlanVersion[]`, oldest first) and non-destructive revert
(restores a past layout as a new version).

### `GET /api/v1/plans/{id}/export` · `POST /api/v1/plans/import`

Export returns a portable `PlanExport` `{name, description, layout,
exported_at}` (no server ids); import creates a new plan from that document.

The plan `summary` is derived server-side: `total_power_mw`
(`Σ power_mw × clock^1.321928`), `machine_count`, `machine_counts`
(building id → count), and `build_cost` (item id → total quantity).

## Endpoints (Phase 5 — Production Planner)

### `GET /api/v1/gamedata/recipes` · `GET /api/v1/gamedata/items`

`RecipeInfo[]` (`{id, name, machine, duration_seconds, inputs, outputs,
is_alternate, unlock}`, rates items/min) and `ItemInfo[]` (`{id, name, category,
stack_size, is_fluid, sink_points}`). Static, cached.

### `POST /api/v1/production/plan`

Body `ProductionRequest` `{item, rate_per_min, recipe_overrides?: {item:
recipe_id}, somersloop_items?: [item]}` → `ProductionPlan` `{target, root,
totals, warnings}`. `root` is a `ProductionNode` tree (`{item, rate_per_min,
is_raw, recipe_id, machine, machine_count, power_mw, somersloop, byproducts,
inputs}`); `totals` carries `power_mw`, `machine_counts`, `raw_materials`,
`byproducts`, and a `build_cost` shopping list. An unknown override recipe →
`404 not_found`; cycles / missing machines are reported in `warnings`.
Somersloop-amplified nodes double output at `×4` per-machine power.

## Endpoints (Phase 6 — Logistics)

### `GET /api/v1/gamedata/transport`

`TransportData` `{belts, pipes: [{id, name, rate}], vehicles: [{id, name,
capacity_slots?, power_mw?, fuel?}]}`. Static, cached.

### `GET /api/v1/logistics`

`LogisticsSnapshot`: `nodes` (`{id, name, type, position}`), `routes`
(`{id, name, mode, tier, item, throughput_per_min, capacity_per_min, from_node,
to_node, utilization, over_capacity}` — the last two derived server-side),
`trains` (live, also streamed on WS topic `logistics.trains`), and a `summary`
(`route_count`, `node_count`, `over_capacity_routes`, `throughput_by_mode`,
`max_utilization`).

## Endpoints (Phase 7 — Power)

### `GET /api/v1/gamedata/power`

`PowerBuildingInfo[]` (`{id, name, power_mw, fuel?, fuel_rate?, requires_water,
water_rate?, capacity_mwh?, max_charge_mw?}`). Static, cached.

### `GET /api/v1/power?history=<n>`

`PowerReport`: live `power` (`PowerStats`), `headroom_mw` / `headroom_percent`,
`status` (ok|warn|critical), `battery` (`{percent, capacity_mwh, stored_mwh,
trend, minutes_remaining}`), a `recommendations` list, and recent `history`
(`PowerHistoryPoint[]`, ≤`history`). Live grid stats also arrive on
`dashboard.snapshot`.

## Endpoints (Phase 8 — Blueprint System)

### `GET /api/v1/blueprints` · `POST /api/v1/blueprints`

List returns `BlueprintSummary[]` (no `data` body), newest first, filtered by
optional `category`, `tag`, `favorite`, and `q` (name/description search) query
params. POST body `BlueprintIn` `{name, description?, category?, tags?, favorite?,
data?}` → 201 `Blueprint` (summary + `data`).

### `GET/PUT/DELETE /api/v1/blueprints/{id}`

GET → full `Blueprint`. PUT body `BlueprintUpdate` (partial; only supplied fields
change, including toggling `favorite`). DELETE → 204.

### `GET /api/v1/blueprints/stats`

`BlueprintStats` `{total, favorites, by_category, by_tag}`.

### `GET /api/v1/blueprints/{id}/export` · `POST /api/v1/blueprints/import`

Export → portable `BlueprintExport` (no server ids); import creates a new
blueprint from that document.

## WebSocket `/ws`

Client → server:

```json
{ "action": "subscribe", "topics": ["power.*", "system.heartbeat"] }
{ "action": "unsubscribe" }
{ "action": "ping" }
```

Server → client (every message):

```json
{ "topic": "system.heartbeat", "timestamp": "…", "payload": { "alive": true } }
```

`_system` is a reserved topic for acks, pongs, and protocol errors. A new
`subscribe` replaces the previous topic set. Topic catalog:
`shared/constants/ws_topics.json`.
