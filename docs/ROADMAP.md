# Roadmap

Development proceeds strictly phase by phase; the project stays buildable at
every step.

| Phase | Scope | Status |
|---|---|---|
| 1 | **Foundation** — config, logging, error handling, API framework, database, WebSocket server, scheduler, frontend shell | ✅ done |
| 2 | **Dashboard** — factory status, power, production, storage, alerts, efficiency, machine counts, graphs | ✅ done (simulated data source until Phase 11) |
| 3 | **World Map** — interactive map, players, factories, nodes, trains, stations, markers, search, filters, layers | ✅ done (simulated data; no terrain tiles yet) |
| 4 | **Factory Planner** — grid designer, placement, blueprint editor, area planning, import/export, versioning | ✅ done (simulated/static game data) |
| 5 | **Production Planner** — recipes, clocks, somersloops, alternates, balancing, power calc, shopping lists | ✅ done (static recipe data; seed subset) |
| 6 | **Logistics** — belts, pipes, trains, trucks, drones, flow visualization, throughput analysis | ✅ done (simulated network) |
| 7 | **Power** — power graph, history, consumption/generation, batteries, recommendations | ✅ done (simulated data) |
| 8 | **Blueprint System** — library, categories, tags, search, favorites, import/export, statistics | ⬜ next |
| 9 | **Analytics** — historical graphs, uptime, production/power history, comparisons, KPIs | ⬜ |
| 10 | **AI Advisor** — bottleneck/shortage/starvation detection with explained recommendations | ⬜ |
| 11 | **FRM Integration** — discovery, reconnect, health, caching, WS + polling fallback, normalization | ⬜ |
| 12 | **Offline Mode** — save-file reading, planning without a live game | ⬜ |

## Cross-cutting backlog

- Alembic migrations (before Phase 2 history tables).
- Auth enforcement middleware (before any remote-exposure guidance).
- OpenAPI-generated frontend types (before the API contract grows past Phase 2).
- Full game-data import script (`scripts/import_game_data.py`).
- E2E test suite in `tests/` (Playwright) once Phase 2 UI exists.
- Plugin runtime per `docs/PLUGIN_GUIDE.md`.

Note: the spec lists FRM integration as Phase 11, but Phases 2–3 need live data
to be useful — expect a minimal FRM read path to be pulled forward into Phase 2,
with the full connector (discovery, caching, fallback) completed in Phase 11.
