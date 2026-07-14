"""Optional error tracing and low-volume HTTP performance telemetry."""

from __future__ import annotations

import logging
import os
import time


LOGGER = logging.getLogger("msi.http")
_SENSITIVE_HEADERS = {"authorization", "cookie", "set-cookie", "x-api-key"}


def _env_float(name: str, default: float) -> float:
    try:
        return float(str(os.environ.get(name, "") or "").strip() or default)
    except ValueError:
        return default


def configure_error_reporting() -> bool:
    dsn = str(os.environ.get("SENTRY_DSN", "") or "").strip()
    if not dsn:
        return False
    try:
        import sentry_sdk
    except ImportError:
        LOGGER.warning("SENTRY_DSN is configured but sentry-sdk is not installed.")
        return False
    sentry_sdk.init(
        dsn=dsn,
        environment=str(os.environ.get("APP_ENV", "production") or "production"),
        traces_sample_rate=min(max(_env_float("SENTRY_TRACES_SAMPLE_RATE", 0.05), 0.0), 1.0),
        send_default_pii=False,
        before_send=_filter_sensitive_event,
    )
    return True


def _filter_sensitive_event(event, _hint):
    """Remove credentials and request bodies before an event leaves the process."""
    request = event.get("request") if isinstance(event, dict) else None
    if isinstance(request, dict):
        headers = request.get("headers")
        if isinstance(headers, dict):
            request["headers"] = {
                key: ("[Filtered]" if str(key).casefold() in _SENSITIVE_HEADERS else value)
                for key, value in headers.items()
            }
        if "data" in request:
            request["data"] = "[Filtered]"
        request.pop("cookies", None)
    user = event.get("user") if isinstance(event, dict) else None
    if isinstance(user, dict):
        for key in ("email", "ip_address", "username"):
            user.pop(key, None)
    return event


class RequestMetricsMiddleware:
    """Log only slow, large, or failed requests without recording query values."""

    def __init__(self, app):
        self.app = app
        self.slow_ms = max(_env_float("HTTP_SLOW_REQUEST_MS", 500.0), 0.0)
        self.large_bytes = max(int(_env_float("HTTP_LARGE_RESPONSE_BYTES", 150_000)), 0)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        started = time.perf_counter()
        status_code = 500
        response_bytes = 0

        async def send_with_metrics(message):
            nonlocal status_code, response_bytes
            if message["type"] == "http.response.start":
                status_code = int(message.get("status", 500))
            elif message["type"] == "http.response.body":
                response_bytes += len(message.get("body", b"") or b"")
            await send(message)

        try:
            await self.app(scope, receive, send_with_metrics)
        finally:
            elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
            if (
                status_code >= 500
                or elapsed_ms >= self.slow_ms
                or response_bytes >= self.large_bytes
            ):
                request_id = str(scope.get("state", {}).get("request_id", "") or "")
                log = LOGGER.error if status_code >= 500 else LOGGER.info
                log(
                    "http_request request_id=%s method=%s path=%s status=%s duration_ms=%s response_bytes=%s",
                    request_id or "unavailable",
                    scope.get("method", ""),
                    scope.get("path", ""),
                    status_code,
                    elapsed_ms,
                    response_bytes,
                )


__all__ = ["RequestMetricsMiddleware", "configure_error_reporting"]
