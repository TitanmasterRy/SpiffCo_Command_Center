# SpiffCo Command Center — Backend

FastAPI application that talks to Ficsit Remote Monitoring, normalizes game data,
persists history, and serves the frontend over REST + WebSockets.

## Run

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    POSIX: source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

- OpenAPI docs: http://localhost:8000/docs
- Health: http://localhost:8000/api/v1/health
- WebSocket: ws://localhost:8000/ws

## Test / lint

```bash
pytest
ruff check app tests
mypy app
```

## Layout

```
app/
  main.py       Application factory & lifespan
  errors.py     AppError hierarchy + exception handlers
  config/       Settings (pydantic-settings) and logging setup
  api/          REST routers (v1) + WebSocket endpoint
  services/     Business logic (event bus, system service, …)
  models/       SQLAlchemy ORM models
  schemas/      Pydantic request/response models
  database/     Engine, session factory, initialization
  workers/      Background task scheduler & periodic jobs
  connectors/frm/  FRM client (Phase 11)
  …             Domain packages (planner, power, logistics, …) filled in later phases
tests/          Pytest suite
```

Configuration is environment-driven (`SPIFFCO_` prefix); see `../.env.example`.
