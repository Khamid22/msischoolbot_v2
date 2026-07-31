"""HTTP readiness and runtime state for the standalone Telegram bot."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock, Thread

LOGGER = logging.getLogger("msi.telegram.health")


@dataclass
class BotHealthState:
    """Thread-safe Telegram polling state exposed without sensitive values."""

    polling_state: str = "starting"
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)

    def set_polling_state(self, polling_state: str) -> None:
        with self._lock:
            self.polling_state = polling_state

    def snapshot(self) -> dict[str, str]:
        with self._lock:
            polling_state = self.polling_state
        service_name = str(os.getenv("RAILWAY_SERVICE_NAME", "") or "").strip()
        return {
            "status": "ready",
            "service": service_name or "lms-telegram-bot",
            "polling": polling_state,
        }


BOT_HEALTH_STATE = BotHealthState()


class _BotHealthHandler(BaseHTTPRequestHandler):
    health_state = BOT_HEALTH_STATE

    def do_GET(self) -> None:  # noqa: N802 - inherited HTTP handler name
        if self.path != "/health/ready":
            self.send_error(404)
            return
        body = json.dumps(self.health_state.snapshot()).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        LOGGER.debug(format, *args)


@dataclass
class BotHealthServer:
    server: ThreadingHTTPServer
    thread: Thread

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


def start_bot_health_server(
    *,
    host: str,
    port: int,
    health_state: BotHealthState = BOT_HEALTH_STATE,
) -> BotHealthServer:
    handler = type(
        "BotHealthHandler",
        (_BotHealthHandler,),
        {"health_state": health_state},
    )
    server = ThreadingHTTPServer((host, port), handler)
    server.daemon_threads = True
    thread = Thread(
        target=server.serve_forever,
        name="telegram-bot-health",
        daemon=True,
    )
    thread.start()
    LOGGER.info("bot_health_started host=%s port=%s", host, server.server_port)
    return BotHealthServer(server=server, thread=thread)


__all__ = [
    "BOT_HEALTH_STATE",
    "BotHealthServer",
    "BotHealthState",
    "start_bot_health_server",
]
