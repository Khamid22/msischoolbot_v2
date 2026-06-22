#!/bin/sh
# Railway web start: bind uvicorn to Railway's injected $PORT on all interfaces.
# (No pre-flight import — that only added a startup failure mode for no benefit.)
set -eu

echo "railway_start: port=${PORT:-8080}"
exec uvicorn web.backend.server:app --host 0.0.0.0 --port "${PORT:-8080}"
