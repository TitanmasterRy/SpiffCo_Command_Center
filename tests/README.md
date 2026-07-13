# Tests

Unit tests live next to their stack:

- Backend: `backend/tests/` (pytest) — `cd backend && pytest`
- Frontend: `frontend/src/tests/` (vitest) — `cd frontend && npm test`

This directory is reserved for cross-stack **end-to-end tests** (Playwright
against a running docker-compose stack), planned once Phase 2 ships real UI.
