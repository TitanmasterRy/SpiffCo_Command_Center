FROM python:3.12-slim

WORKDIR /srv/app

COPY backend/pyproject.toml backend/README.md ./
COPY backend/app ./app
RUN pip install --no-cache-dir .

# Static game data lives at the repo root; the app resolves it at /srv/database.
COPY database /srv/database

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
