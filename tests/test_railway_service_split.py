"""Deployment contract for independently operated LMS services."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _config(service_name: str) -> dict:
    path = ROOT / "deploy" / f"railway.{service_name}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_backend_is_the_only_lms_service_that_runs_migrations():
    backend = _config("backend")
    bot = _config("bot")
    frontend = _config("frontend")

    assert backend["deploy"]["preDeployCommand"] == "python -m alembic upgrade head"
    assert "preDeployCommand" not in bot["deploy"]
    assert "preDeployCommand" not in frontend["deploy"]


def test_lms_services_have_independent_runtime_contracts():
    backend = _config("backend")
    bot = _config("bot")
    frontend = _config("frontend")

    assert backend["deploy"]["startCommand"] == "python main.py web"
    assert bot["deploy"]["startCommand"] == "python main.py bot"
    assert bot["build"]["dockerfilePath"] == "deploy/Dockerfile.bot"
    assert frontend["build"]["dockerfilePath"] == "deploy/Dockerfile.frontend"
    assert {
        backend["deploy"]["healthcheckPath"],
        bot["deploy"]["healthcheckPath"],
        frontend["deploy"]["healthcheckPath"],
    } == {"/health/ready"}


def test_frontend_gateway_preserves_same_origin_backend_routes():
    caddyfile = (ROOT / "deploy" / "frontend.Caddyfile").read_text(encoding="utf-8")

    assert "handle /static/react/*" in caddyfile
    assert "reverse_proxy {$BACKEND_INTERNAL_URL}" in caddyfile
    assert 'header Cache-Control "no-cache"' in caddyfile
