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

## Free public deploy — Fly.io (single image)

For a shareable public URL, the root `Dockerfile` builds one image where the
FastAPI backend serves the compiled SPA on the same origin (no nginx, no CORS).
`fly.toml` wires it up with a persistent volume for SQLite.

```bash
# from the repo root, once:
fly launch --no-deploy --copy-config --name spiffco-command-center
fly volumes create spiffco_data --size 1 --region iad
fly deploy
# afterwards, redeploys are just:
fly deploy
```

This runs on **simulation + offline (save-upload) data**: a cloud machine cannot
reach a game running on your PC, so `SPIFFCO_FRM_ENABLED` stays `false` here. The
machine scales to zero when idle (free-tier friendly) and wakes on the next
request. The same image runs anywhere that takes a Dockerfile (Render, Railway,
Koyeb) — set `SPIFFCO_STATIC_DIR=/srv/app/static` and a writable
`SPIFFCO_DATABASE_URL` (their free Postgres works: see below).

The single-image serving is controlled by `SPIFFCO_STATIC_DIR` (path to the built
`dist/`); leave it empty in dev, where Vite serves the frontend separately.

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
