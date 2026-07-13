# Known Limitations

Current, deliberate limitations — each has a planned resolution.

| Limitation | Why | Planned fix |
|---|---|---|
| No Alembic migrations (`create_all` only) | Tables so far are additive; `create_all` still safe | Introduce Alembic before the first schema *change* (not addition) |
| Providers are simulated unless `SPIFFCO_FRM_ENABLED` | Default install has no live game | Enable FRM to poll a live mod; falls back to simulation if unreachable |
| FRM field mapping unvalidated against a live mod | Built without game access, from the FRM API shape | Validate/adjust `app/connectors/frm/normalize.py` against a running mod; capture fixtures |
| FRM logistics routes are empty (nodes/trains only) | Belt/pipe throughput isn't exposed by FRM | Derive rail routes from train timetables; belts stay planner-only |
| Offline save parser extracts header + building counts only (no positions/inventories) | The `.sav` property blob is intricate and version-fragile; counts are read robustly by scanning actor instance names | Add per-actor transform parsing (map/logistics from saves) once fixtures exist |
| Offline power figures are estimates | A static save has no live production/consumption; values use nominal building power at 100% clock | Refine with recipe/clock data from the save when property parsing lands |
| Offline mode leaves the World Map / Logistics pages empty | Positions aren't extracted from saves | Same per-actor transform parsing above |
| Frontend bundle >830 kB (Recharts/Leaflet) | Single chunk for simplicity | Code-split chart/map pages |
| Auth settings exist but are not enforced | No remote-exposure features yet; localhost assumed | Auth middleware before documenting remote access |
| Game data files are seed subsets | Hand-curated for planner development | `scripts/import_game_data.py` from game `Docs.json` |
| Frontend types mirrored by hand | Contract is tiny | Generate from OpenAPI before the contract grows |
| Single-process only (in-process bus, asyncio scheduler) | Self-hosted simplicity | Interfaces allow Redis-backed bus if ever needed |
| No E2E tests | No real UI flows yet | Playwright suite in `tests/` after Phase 2 |
| WebSocket has no per-client auth | Follows API auth status | Same auth middleware work |
| SQLite `DateTime` stored naive | SQLite has no tz-aware type | Values are always UTC; revisit on PostgreSQL migration |
