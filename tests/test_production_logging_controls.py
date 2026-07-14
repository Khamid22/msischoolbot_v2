"""Regression coverage for production log-volume controls."""

from __future__ import annotations

from types import SimpleNamespace

import main
from backend.core.runtime import performance
from backend.server import handle_unexpected_error


def _clear_railway_environment(monkeypatch):
    for name in (
        "RAILWAY_PROJECT_ID",
        "RAILWAY_ENVIRONMENT_ID",
        "RAILWAY_SERVICE_ID",
    ):
        monkeypatch.delenv(name, raising=False)


def test_uvicorn_access_logs_remain_enabled_locally(monkeypatch):
    _clear_railway_environment(monkeypatch)
    monkeypatch.delenv("UVICORN_ACCESS_LOG", raising=False)

    assert main._uvicorn_access_log_enabled() is True


def test_uvicorn_access_logs_default_to_disabled_on_railway(monkeypatch):
    _clear_railway_environment(monkeypatch)
    monkeypatch.setenv("RAILWAY_PROJECT_ID", "project-id")
    monkeypatch.delenv("UVICORN_ACCESS_LOG", raising=False)

    assert main._uvicorn_access_log_enabled() is False


def test_uvicorn_access_log_override_is_respected(monkeypatch):
    monkeypatch.setenv("RAILWAY_PROJECT_ID", "project-id")
    monkeypatch.setenv("UVICORN_ACCESS_LOG", "true")

    assert main._uvicorn_access_log_enabled() is True


def test_fast_page_performance_is_suppressed_in_production(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("PAGE_PERFORMANCE_LOG_MIN_MS", raising=False)
    messages = []
    monkeypatch.setattr(performance.LOGGER, "info", lambda *args, **kwargs: messages.append(args))
    timer = SimpleNamespace(total_ms=lambda: 100.0, timings={"render_ms": 100.0})

    performance.log_page_performance("fast_page", timer)

    assert messages == []


def test_slow_page_performance_remains_visible_in_production(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("PAGE_PERFORMANCE_LOG_MIN_MS", raising=False)
    messages = []
    monkeypatch.setattr(performance.LOGGER, "info", lambda *args, **kwargs: messages.append(args))
    timer = SimpleNamespace(total_ms=lambda: 300.0, timings={"render_ms": 300.0})

    performance.log_page_performance("slow_page", timer)

    assert len(messages) == 1


def test_unexpected_error_log_is_one_line_and_identifies_exception(monkeypatch):
    messages = []
    monkeypatch.setattr(
        "backend.server.LOGGER.error",
        lambda *args, **kwargs: messages.append((args, kwargs)),
    )
    request = SimpleNamespace(
        method="GET",
        url=SimpleNamespace(path="/internal/operations"),
        headers={},
        state=SimpleNamespace(request_id="request-123"),
    )

    response = handle_unexpected_error(request, ValueError("line one\nline two"))

    assert response.status_code == 500
    assert "request-123" in response.body.decode("utf-8")
    assert len(messages) == 1
    assert "request_id=%s" in messages[0][0][0]
    assert "ValueError" in messages[0][0]
    assert "line one line two" in messages[0][0]
    assert "request-123" in messages[0][0]
    assert messages[0][1] == {}
