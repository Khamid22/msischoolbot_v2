#!/bin/sh
# Railway start: bind FastAPI to Railway's injected $PORT and run bot polling.
set -eu

export RUN_MODE="${RUN_MODE:-both}"
echo "railway_start: port=${PORT:-8080} run_mode=${RUN_MODE}"

# Apply database migrations before starting. If this fails the deploy aborts and
# Railway keeps the previous (healthy) container running — no downtime.
echo "railway_start: applying alembic migrations..."
python -m alembic upgrade head

exec python main.py "${RUN_MODE}"
