"""Standalone worker health endpoint tests."""

from __future__ import annotations

import json
from urllib.request import urlopen

from backend.application.worker_health import start_worker_health_server


def test_worker_health_server_reports_readiness():
    health_server = start_worker_health_server(host="127.0.0.1", port=0)
    try:
        with urlopen(  # noqa: S310 - local test server only
            f"http://127.0.0.1:{health_server.server.server_port}/health/ready",
            timeout=2,
        ) as response:
            assert response.status == 200
            assert json.load(response) == {
                "status": "ready",
                "service": "finance-worker",
            }
    finally:
        health_server.close()
