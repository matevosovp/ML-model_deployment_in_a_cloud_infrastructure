#!/usr/bin/env bash
set -e

PORT="${PORT:-8000}"
HOST="${HOST:-0.0.0.0}"

echo "Starting uvicorn on ${HOST}:${PORT}"
echo "Open: http://localhost:${PORT}/docs"

uvicorn services.ml_service.main:app --host "$HOST" --port "$PORT" --reload
