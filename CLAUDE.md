# CLAUDE.md — Project guide for AI assistants

## What this is

SpiffCo Command Center: a self-hosted web app that connects to Satisfactory via the
Ficsit Remote Monitoring (FRM) mod and provides a live operations center (dashboard,
map, planners, power, logistics, blueprints, analytics, advisor).

## Ground rules

- **Production quality, not prototype.** Strong typing, docstrings on public APIs,
  unit tests for new behavior, no duplicated logic.
- **Work phase by phase** (see `docs/ROADMAP.md`). Do not skip ahead; keep the
  project buildable at all times.
- **Never expose raw FRM responses to the frontend** — normalize into internal
  schemas (`backend/app/schemas/`).
- Document trade-offs in `docs/` before implementing uncertain designs.

## Stack

- Backend: Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2 (async), SQLite
  (Postgres-ready), WebSockets, asyncio scheduler. Entry: `backend/app/main.py`.
- Frontend: React 18, TypeScript (strict), Vite, TailwindCSS, React Router,
  TanStack Query, Zustand. Entry: `frontend/src/main.tsx`.
- Static game data: JSON in `database/data/` (see `docs/DATABASE_SCHEMA.md`).

## Commands

- Backend dev: `cd backend && uvicorn app.main:app --reload --port 8000`
- Backend tests: `cd backend && pytest`
- Frontend dev: `cd frontend && npm run dev`
- Frontend build: `cd frontend && npm run build`
- Frontend tests: `cd frontend && npm test`

## Conventions

- Backend settings: `pydantic-settings`, env prefix `SPIFFCO_`, defined in
  `backend/app/config/settings.py`. Never read `os.environ` directly elsewhere.
- API: versioned under `/api/v1`; routers live in `backend/app/api/v1/`,
  business logic in `backend/app/services/` (routers stay thin).
- Errors: raise `AppError` subclasses (`backend/app/errors.py`); handlers produce
  the standard error envelope. Don't return ad-hoc error dicts.
- Realtime: publish through the `EventBus` (`backend/app/services/event_bus.py`);
  the WebSocket layer subscribes to topics. Don't push to sockets directly
  from services.
- Frontend: pages in `src/pages/`, shared UI in `src/components/`, server state via
  TanStack Query hooks in `src/hooks/`, client state via Zustand in `src/stores/`.
  All backend types mirrored in `src/types/`.

## Style

- Python: ruff + mypy clean; Google-style docstrings.
- TypeScript: strict mode; functional components; no default exports except pages.
- See `docs/CODING_STANDARDS.md` for the full standard.
