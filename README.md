# SpiffCo Command Center

A self-hosted operations center for **Satisfactory**, powered by
[Ficsit Remote Monitoring (FRM)](https://docs.ficsit.app/ficsitremotemonitoring/latest/).

SpiffCo Command Center connects to your running Satisfactory session and gives you a
live SCADA-style view of your factories: production, power, logistics, blueprints,
world map, planning tools, and an advisor engine — all in one unified web interface.

> Think *Satisfactory Tools* + *Grafana* + *Google Maps* + *ERP*, self-hosted, for your save.

## Status

**Phases 1–2 complete** (foundation + dashboard, on simulated data until FRM lands).
See [PROJECT_STATE.md](PROJECT_STATE.md) for the full complete/incomplete breakdown
and [docs/ROADMAP.md](docs/ROADMAP.md) for the 12-phase plan.

| Area | Status |
|---|---|
| Backend API framework (FastAPI) | ✅ |
| Configuration & logging | ✅ |
| Error handling | ✅ |
| Database layer (SQLite / SQLAlchemy) | ✅ |
| WebSocket server & event bus | ✅ |
| Background task scheduler | ✅ |
| Frontend shell (React + Vite + Tailwind) | ✅ |
| Dashboard, Map, Planner, … | 🚧 Later phases |

## Quick start

### Prerequisites

- Python ≥ 3.11
- Node.js ≥ 20
- Satisfactory with the FRM mod (optional — the app runs without it in offline mode)

### Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate    POSIX: source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs — health check: http://localhost:8000/api/v1/health

### Frontend

```bash
cd frontend
npm install
npm run dev
```

UI: http://localhost:5173 (proxies `/api` and `/ws` to the backend).

### Docker

```bash
docker compose up --build
```

## Configuration

Copy `.env.example` to `.env` and adjust. All backend settings use the `SPIFFCO_`
prefix and are documented in the example file.

## Project layout

```
backend/    FastAPI application (API, services, FRM connector, workers)
frontend/   React + TypeScript + Vite UI
shared/     Types, constants and schemas shared across the stack
database/   Static game data (recipes, buildings, items, …) as JSON
docs/       Architecture, API reference, guides
scripts/    Development & maintenance scripts
plugins/    Plugin system (see docs/PLUGIN_GUIDE.md)
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Developer guide](docs/DEVELOPER_GUIDE.md)
- [API reference](docs/API_REFERENCE.md)
- [Database schema](docs/DATABASE_SCHEMA.md)
- [Deployment guide](docs/DEPLOYMENT.md)
- [Plugin guide](docs/PLUGIN_GUIDE.md)
- [Coding standards](docs/CODING_STANDARDS.md)
- [Roadmap](docs/ROADMAP.md)
- [Known limitations](docs/KNOWN_LIMITATIONS.md)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE).
