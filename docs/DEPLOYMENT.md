# Deployment Guide

## Docker Compose (recommended)

```bash
cp .env.example .env   # optional overrides
docker compose up --build -d
```

- UI: http://localhost:8080 (nginx serving the built frontend, proxying
  `/api` and `/ws` to the backend container)
- API: http://localhost:8000
- Data persists in the `spiffco-data` volume (SQLite file).

Point the backend at your game machine by setting `SPIFFCO_FRM_BASE_URL`
(defaults to `http://host.docker.internal:8080` in the compose file — adjust to
the host/port where the FRM mod's web server listens).

## Bare metal

1. Backend: `pip install .` inside `backend/`, then run under a process manager:
   ```
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
2. Frontend: `npm run build` in `frontend/`, serve `dist/` with any static file
   server, and reverse-proxy `/api` and `/ws` to the backend (see
   `frontend/nginx.conf` for a working nginx config).

## Production checklist

- Set `SPIFFCO_ENVIRONMENT=production` and `SPIFFCO_DEBUG=false`.
- Restrict `SPIFFCO_CORS_ORIGINS` to your UI origin.
- Enable auth if the instance is reachable beyond localhost:
  `SPIFFCO_AUTH_ENABLED=true`, `SPIFFCO_AUTH_TOKEN=<long random string>`.
  (Enforcement middleware ships before any remote-exposure features; until
  then, do not expose the API to untrusted networks.)
- Back up the SQLite database file (it lives in the `spiffco-data` volume).

## Upgrading to PostgreSQL

Set `SPIFFCO_DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/spiffco`
and add `asyncpg` to the environment. No code changes required.
