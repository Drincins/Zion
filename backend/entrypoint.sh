#!/usr/bin/env sh
set -e

# Decide whether to run Alembic migrations. Some databases are provisioned
# from a prebuilt dump that lacks the Alembic history tables; in that case
# running migrations will fail because base tables (like users) are absent.

should_run=$(python - <<'PY'
import os
from sqlalchemy import create_engine, text

# Build the same URL the application uses
url = os.getenv("DATABASE_URL")
if not url:
    host = os.getenv("POSTGRES_HOST", "db")
    port = os.getenv("POSTGRES_PORT", "5432")
    user = os.getenv("POSTGRES_USER", "zion_user")
    password = os.getenv("POSTGRES_PASSWORD", "supersecret")
    database = os.getenv("POSTGRES_DB", "zion")
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"

engine = create_engine(url, future=True)

with engine.connect() as conn:
    # Only attempt Alembic migrations if the history table is present.
    result = conn.execute(
        text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = 'alembic_version'
            )
            """
        )
    ).scalar()
    print("yes" if result else "no")
PY
)

if [ "$should_run" = "yes" ]; then
  echo "Running Alembic migrations before starting the app..."
  alembic upgrade heads
else
  echo "Skipping Alembic migrations because alembic_version table is missing."
fi

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
