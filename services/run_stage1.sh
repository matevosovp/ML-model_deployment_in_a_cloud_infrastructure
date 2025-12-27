#!/usr/bin/env bash
set -euo pipefail

HOST="${APP_HOST:-0.0.0.0}"
PORT="${APP_PORT_STAGE1:-8000}"

echo "Starting uvicorn on ${HOST}:${PORT}"
echo "Open: http://localhost:${PORT}/docs"

python3 -m uvicorn ml_service.main:app --host "${HOST}" --port "${PORT}" --reload
