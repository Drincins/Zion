#!/usr/bin/env sh
set -e

echo "Running Alembic migrations before starting the app..."
alembic upgrade head

cpu_count="$(getconf _NPROCESSORS_ONLN 2>/dev/null || printf '1')"
case "$cpu_count" in
  ''|*[!0-9]*) cpu_count=1 ;;
esac
if [ "$cpu_count" -lt 1 ]; then
  cpu_count=1
fi
if [ "$cpu_count" -gt 8 ]; then
  cpu_count=8
fi

BACKEND_WORKERS="${BACKEND_WORKERS:-$cpu_count}"
BACKEND_KEEP_ALIVE="${BACKEND_KEEP_ALIVE:-30}"
BACKEND_TIMEOUT="${BACKEND_TIMEOUT:-120}"
BACKEND_GRACEFUL_TIMEOUT="${BACKEND_GRACEFUL_TIMEOUT:-30}"
BACKEND_LOG_LEVEL="${BACKEND_LOG_LEVEL:-info}"

echo "Starting backend with workers=${BACKEND_WORKERS}, keep-alive=${BACKEND_KEEP_ALIVE}s, timeout=${BACKEND_TIMEOUT}s"

exec gunicorn app.main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${BACKEND_WORKERS}" \
  --keep-alive "${BACKEND_KEEP_ALIVE}" \
  --timeout "${BACKEND_TIMEOUT}" \
  --graceful-timeout "${BACKEND_GRACEFUL_TIMEOUT}" \
  --log-level "${BACKEND_LOG_LEVEL}" \
  --access-logfile - \
  --error-logfile - \
  --worker-tmp-dir /dev/shm
