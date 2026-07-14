#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -f "${SCRIPT_DIR}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${SCRIPT_DIR}/.env"
  set +a
fi

HOST="${APP_HOST:-127.0.0.1}"
PORT="${APP_PORT_STAGE1:-8000}"

echo "Starting uvicorn on ${HOST}:${PORT}"
echo "Open: http://localhost:${PORT}/docs"

cd "${SCRIPT_DIR}"
python3 -m uvicorn ml_service.main:app --host "${HOST}" --port "${PORT}" --reload
