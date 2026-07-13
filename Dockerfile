# Single-image build: compiles the React frontend, then serves it from the
# FastAPI backend on one origin (so /api and /ws need no proxy or CORS).
# Used by the Fly.io deploy (see fly.toml). For the two-container LAN setup that
# talks to a live game, use docker-compose.yml instead.

# 1. Build the SPA.
FROM node:20-alpine AS frontend
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# 2. Backend runtime, bundling the compiled SPA.
FROM python:3.12-slim
WORKDIR /srv/app

COPY backend/pyproject.toml backend/README.md ./
COPY backend/app ./app
RUN pip install --no-cache-dir .

# Serve the built frontend from the API (see app.main.mount_frontend).
COPY --from=frontend /app/dist ./static

ENV SPIFFCO_STATIC_DIR=/srv/app/static \
    SPIFFCO_HOST=0.0.0.0 \
    SPIFFCO_PORT=8000 \
    SPIFFCO_ENVIRONMENT=production \
    SPIFFCO_DEBUG=false

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
