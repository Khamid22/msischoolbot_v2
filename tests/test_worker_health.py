"""Standalone worker health endpoint tests."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.request import urlopen

from backend.application.worker_health import start_worker_health_server

ROOT = Path(__file__).resolve().parents[1]


def test_worker_health_server_reports_configured_service(monkeypatch):
    monkeypatch.setenv("WORKER_ID", "curriculum-worker")
    health_server = start_worker_health_server(host="127.0.0.1", port=0)
    try:
        with urlopen(  # noqa: S310 - local test server only
            f"http://127.0.0.1:{health_server.server.server_port}/health/ready",
            timeout=2,
        ) as response:
            assert response.status == 200
            assert json.load(response) == {
                "status": "ready",
                "service": "curriculum-worker",
            }
    finally:
        health_server.close()


def test_curriculum_worker_image_installs_presentation_tools_only_for_its_service():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert 'ARG RAILWAY_SERVICE_NAME' in dockerfile
    assert '[ "$RAILWAY_SERVICE_NAME" = "curriculum-worker" ]' in dockerfile
    assert "libreoffice-impress" in dockerfile
    assert "poppler-utils" in dockerfile
