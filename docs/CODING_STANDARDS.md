# Coding Standards

## General

- Production quality: every public function/class documented, unit tests for
  new behavior, no duplicated logic, small composable units.
- Composition over inheritance; dependency injection over globals; no global
  mutable state (module-level singletons are wired through app state or DI).

## Python (backend)

- Python ≥ 3.11, `ruff` (line length 100) and `mypy --strict` clean.
- Google-style docstrings on all public functions, classes, and modules.
- Full type annotations; `Any` requires a justifying comment.
- Settings only via `app.config.settings.get_settings()` — never `os.environ`.
- Expected failures raise `AppError` subclasses; routers never craft error
  responses manually.
- Async end-to-end: no blocking I/O in the event loop (use `httpx`, async
  SQLAlchemy; offload CPU-heavy work).
- Tests: pytest, `asyncio_mode=auto`; test behavior through public interfaces.

## TypeScript (frontend)

- `strict` mode; no `any` without a justifying comment.
- Functional components only; hooks for all shared behavior.
- Default exports only for route pages; everything else named exports.
- Server state → TanStack Query; client state → Zustand; never mirror server
  data into Zustand.
- Backend schema changes must update `src/types/` in the same PR.
- TSDoc comments on exported components, hooks, and utilities.

## Naming

- Python: `snake_case` modules/functions, `PascalCase` classes.
- TypeScript: `PascalCase` components/types, `camelCase` values, file name
  matches its main export.
- IDs and topics: kebab-case slugs / dotted topics (`power.grid`).

## Commits & PRs

Conventional Commits; one logical change per PR; CHANGELOG updated when
behavior changes. See `CONTRIBUTING.md`.
