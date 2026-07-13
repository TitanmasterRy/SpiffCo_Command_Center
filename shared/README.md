# Shared

Data and definitions used by both the backend and frontend.

```
types/       Cross-stack type notes; the source of truth is backend/app/schemas,
             mirrored by hand in frontend/src/types (see docs/CODING_STANDARDS.md)
constants/   Game and app constants (topics, units, limits) as JSON
recipes/     Reserved for derived/compiled recipe bundles shipped to the frontend
schemas/     JSON Schema documents describing the database/data/*.json files
icons/       Item/building icon assets shared across UI and docs
```

Static game data itself lives in `../database/data/`.
