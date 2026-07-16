#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-real-estate-ml-service}"
CONTAINER_NAME="${CONTAINER_NAME:-real-estate-ml-service}"
ENV_FILE="${ENV_FILE:-.env}"
HOST_PORT="${HOST_PORT:-8001}"
CONTAINER_PORT="${CONTAINER_PORT:-8000}"
BIND_ADDR="${BIND_ADDR:-127.0.0.1}"

echo "Stage 2: Docker run (no compose)"
echo "Image:        ${IMAGE_NAME}"
echo "Container:     ${CONTAINER_NAME}"
echo "Env file:      ${ENV_FILE}"
echo "Bind:          ${BIND_ADDR}:${HOST_PORT} -> ${CONTAINER_PORT}"
echo "Docs:          http://localhost:${HOST_PORT}/docs"
echo "Healthcheck:   http://localhost:${HOST_PORT}/service-status"
echo

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "ERROR: env file not found: ${ENV_FILE}"
  exit 1
fi

if docker ps -a --format '{{.Names}}' | grep -qx "${CONTAINER_NAME}"; then
  echo "Removing existing container ${CONTAINER_NAME}..."
  docker rm -f "${CONTAINER_NAME}" >/dev/null
fi

echo "Building image..."
docker build -t "${IMAGE_NAME}" -f Dockerfile_ml_service .

echo "Starting container..."
docker run --rm --name "${CONTAINER_NAME}" \
  --env-file "${ENV_FILE}" \
  --init \
  --read-only \
  --tmpfs /tmp:size=64m,mode=1777 \
  --cap-drop ALL \
  --security-opt no-new-privileges:true \
  --pids-limit 256 \
  --memory 1g \
  --cpus 2 \
  -p "${BIND_ADDR}:${HOST_PORT}:${CONTAINER_PORT}" \
  "${IMAGE_NAME}"
