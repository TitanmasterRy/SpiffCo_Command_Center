#!/usr/bin/env bash
# Start backend and frontend dev servers (POSIX). Ctrl-C stops both.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"

(cd "$root/backend" && . .venv/bin/activate && uvicorn app.main:app --reload --port 8000) &
backend_pid=$!
trap 'kill $backend_pid' EXIT

cd "$root/frontend" && npm run dev
