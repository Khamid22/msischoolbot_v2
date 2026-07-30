"""Minimal HTTP readiness endpoint for the standalone Railway worker."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

LOGGER = logging.getLogger("msi.worker.health")


class _WorkerHealthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 - inherited HTTP handler name
        if self.path != "/health/ready":
            self.send_error(404)
            return
        body = json.dumps({"status": "ready", "service": "finance-worker"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        LOGGER.debug(format, *args)


@dataclass
class WorkerHealthServer:
    server: ThreadingHTTPServer
    thread: Thread

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


def start_worker_health_server(*, host: str, port: int) -> WorkerHealthServer:
    server = ThreadingHTTPServer((host, port), _WorkerHealthHandler)
    server.daemon_threads = True
    thread = Thread(
        target=server.serve_forever,
        name="finance-worker-health",
        daemon=True,
    )
    thread.start()
    LOGGER.info("worker_health_started host=%s port=%s", host, server.server_port)
    return WorkerHealthServer(server=server, thread=thread)


__all__ = ["WorkerHealthServer", "start_worker_health_server"]
