#!/bin/sh
# Railway start: bind FastAPI to Railway's injected $PORT and run the web service.
set -eu

export RUN_MODE="${RUN_MODE:-web}"
echo "railway_start: port=${PORT:-8080} run_mode=${RUN_MODE}"

exec python main.py "${RUN_MODE}"
