"""Standalone Telegram bot health endpoint tests."""

from __future__ import annotations

import json
from urllib.request import urlopen

from backend.application.bot_health import BotHealthState, start_bot_health_server


def test_bot_health_server_reports_polling_state(monkeypatch):
    monkeypatch.setenv("RAILWAY_SERVICE_NAME", "LMS-Telegram-Bot")
    health_state = BotHealthState(polling_state="standby")
    health_server = start_bot_health_server(
        host="127.0.0.1",
        port=0,
        health_state=health_state,
    )
    try:
        with urlopen(  # noqa: S310 - local test server only
            f"http://127.0.0.1:{health_server.server.server_port}/health/ready",
            timeout=2,
        ) as response:
            assert response.status == 200
            assert json.load(response) == {
                "status": "ready",
                "service": "LMS-Telegram-Bot",
                "polling": "standby",
            }

        health_state.set_polling_state("active")
        with urlopen(  # noqa: S310 - local test server only
            f"http://127.0.0.1:{health_server.server.server_port}/health/ready",
            timeout=2,
        ) as response:
            assert json.load(response)["polling"] == "active"
    finally:
        health_server.close()
