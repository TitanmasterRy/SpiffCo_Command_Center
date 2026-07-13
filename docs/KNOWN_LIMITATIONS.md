# Known Limitations

Current, deliberate limitations — each has a planned resolution.

| Limitation | Why | Planned fix |
|---|---|---|
| No Alembic migrations (`create_all` only) | History tables are additive; `create_all` still safe | Introduce Alembic before the first schema *change* (not addition) |
| Dashboard data is simulated | FRM connector is Phase 11 | Provider interface already in place; swap in FRM provider |
| Frontend bundle >500 kB (Recharts) | Single chunk for simplicity | Code-split chart pages when more chart-heavy pages exist |
| Auth settings exist but are not enforced | No remote-exposure features yet; localhost assumed | Auth middleware before documenting remote access |
| FRM connector is an interface stub | Spec schedules integration for Phase 11 | Phase 11 (minimal read path may land earlier) |
| Game data files are seed subsets | Hand-curated for planner development | `scripts/import_game_data.py` from game `Docs.json` |
| Frontend types mirrored by hand | Contract is tiny | Generate from OpenAPI before the contract grows |
| Single-process only (in-process bus, asyncio scheduler) | Self-hosted simplicity | Interfaces allow Redis-backed bus if ever needed |
| No E2E tests | No real UI flows yet | Playwright suite in `tests/` after Phase 2 |
| WebSocket has no per-client auth | Follows API auth status | Same auth middleware work |
| SQLite `DateTime` stored naive | SQLite has no tz-aware type | Values are always UTC; revisit on PostgreSQL migration |
