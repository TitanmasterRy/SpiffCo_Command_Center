# Developer Guide

## Setup

1. Prerequisites: Python ≥ 3.11, Node ≥ 20.
2. Backend:
   ```bash
   cd backend
   python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -e ".[dev]"
   uvicorn app.main:app --reload --port 8000
   ```
3. Frontend:
   ```bash
   cd frontend && npm install && npm run dev
   ```
4. Or run both: `scripts/dev.ps1` (Windows) / `scripts/dev.sh` (POSIX).

The Vite dev server proxies `/api` and `/ws` to `localhost:8000`, so the UI at
http://localhost:5173 works against the live backend with zero config.

## Everyday commands

| Task | Command |
|---|---|
| Backend tests | `cd backend && pytest` |
| Backend lint / types | `ruff check app tests` / `mypy app` |
| Frontend tests | `cd frontend && npm test` |
| Frontend build (type-check included) | `npm run build` |

## Adding a feature (checklist)

1. **Schema first**: define/extend Pydantic models in `app/schemas/`.
2. **Service**: implement logic in `app/services/` (or the domain package).
   Raise `AppError` subclasses for expected failures.
3. **Router**: add a thin endpoint in `app/api/v1/`, include it in
   `app/api/v1/__init__.py`.
4. **Realtime?** Publish via the `EventBus`; register the topic in
   `shared/constants/ws_topics.json`.
5. **Frontend**: mirror the schema in `src/types/`, add an endpoint function in
   `src/api/endpoints.ts`, wrap it in a hook, build the UI.
6. **Tests** for service + endpoint (backend) and logic/components (frontend).
7. Update `CHANGELOG.md` and relevant docs.

## Testing notes

- Backend tests run against an in-memory SQLite DB; the `client` fixture boots
  the real app lifespan via `asgi-lifespan`.
- Never hit a real game/FRM instance from tests — Phase 11 ships recorded
  example payloads in `examples/`.

## Debugging

- Set `SPIFFCO_LOG_LEVEL=DEBUG` for verbose logs; `SPIFFCO_LOG_FILE=logs/dev.log`
  to also write to a rotating file.
- WebSocket protocol can be exercised with `npx wscat -c ws://localhost:8000/ws`
  then `{"action":"subscribe","topics":["*"]}` — heartbeats arrive every 15 s.
