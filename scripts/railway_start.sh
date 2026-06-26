#!/bin/sh
# Railway start: bind FastAPI to Railway's injected $PORT and run bot polling.
set -eu

export RUN_MODE="${RUN_MODE:-both}"
echo "railway_start: port=${PORT:-8080} run_mode=${RUN_MODE}"
exec python main.py "${RUN_MODE}"
