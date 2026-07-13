# Architecture

## Overview

```
┌─────────────┐   HTTP/WS    ┌──────────────────────────────┐   REST + WS   ┌──────────┐
│ Satisfactory │ ───────────▶ │        Backend (FastAPI)      │ ────────────▶ │ Frontend │
│  + FRM mod   │              │                                │               │  (React) │
└─────────────┘              │  connectors/frm  ─┐            │               └──────────┘
                              │                   ▼            │
                              │  services ──▶ EventBus ──▶ /ws │
                              │      │                         │
                              │      ▼                         │
                              │  SQLite (history, settings)    │
                              └──────────────────────────────┘
```

The backend is the single integration point with the game. The frontend only
ever sees normalized internal models — **raw FRM responses never cross the API
boundary** (spec requirement; enforced by keeping FRM types private to
`app/connectors/frm`).

## Backend layering

| Layer | Location | Rule |
|---|---|---|
| API | `app/api/` | Thin routers; validation via Pydantic; no business logic |
| Services | `app/services/` | All business logic; raise `AppError` subclasses |
| Schemas | `app/schemas/` | The public contract; only these leave the API |
| Models | `app/models/` | SQLAlchemy ORM; persistence only |
| Connectors | `app/connectors/` | Upstream integrations; normalize at the edge |
| Workers | `app/workers/` | Periodic jobs on the asyncio scheduler |
| Domain packages | `app/planner/`, `app/power/`, … | Pure domain logic per module, filled in by their phase |

## Realtime pipeline

1. Producers (scheduler jobs, later the FRM poller) call `EventBus.publish(topic, payload)`.
2. The bus fans out to subscriptions; each has a **bounded queue** — a slow
   WebSocket client drops its own oldest events instead of blocking producers
   (newest telemetry always wins).
3. `/ws` clients send `{"action": "subscribe", "topics": ["power.*"]}` and
   receive `{topic, timestamp, payload}` envelopes. Topic names are cataloged in
   `shared/constants/ws_topics.json`.

## Key decisions & trade-offs

- **asyncio scheduler instead of Celery/APScheduler** — single self-hosted
  process; no broker to operate. Trade-off: jobs must be async and CPU-light.
  Heavy work (save parsing) will move to a process pool when Phase 12 needs it.
- **SQLite by default** — zero-setup self-hosting. The async SQLAlchemy layer
  and URL-based config make PostgreSQL a config change, not a rewrite.
- **`create_all` now, Alembic later** — schema is tiny and phase 1 iterates
  fast; migrations start once user data is worth preserving (before Phase 2 ships
  history tables). Documented in KNOWN_LIMITATIONS.md.
- **In-process event bus instead of Redis pub/sub** — one process, no external
  dependency. The `EventBus` interface is narrow enough to swap a Redis-backed
  implementation behind it if multi-process deployment is ever needed.
- **Hand-mirrored frontend types** — simple while the contract is small;
  OpenAPI-generated types are on the roadmap before the contract grows.

## Frontend

- **Server state** (health, game data): TanStack Query — caching, polling, retries.
- **Client state** (connection status, UI prefs): Zustand.
- **Realtime**: one `WsClient` (auto-reconnect w/ backoff) mounted at the layout
  root, feeding the connection store; pages subscribe to slices of it.
- Routing via React Router; each page is a lazy-extendable module under `src/pages/`.

## Directory map

See the top-level `README.md` and per-package READMEs; every backend package
carries a docstring stating its phase and purpose.
