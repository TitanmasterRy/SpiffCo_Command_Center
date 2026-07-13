# Shared types

The API contract has one source of truth: **`backend/app/schemas/`** (Pydantic).
The frontend mirrors those models by hand in `frontend/src/types/`.

Planned improvement (tracked in docs/ROADMAP.md): generate the TypeScript types
from the backend's OpenAPI document (`openapi-typescript`) so the mirror can
never drift.
