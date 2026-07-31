"""LMS-owned curriculum worker topology tests."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from types import SimpleNamespace

from backend import server
from backend.application import curriculum_worker
from backend.core.runtime.config import get_app_settings
from backend.modules.domains.academics.subject_curriculum.media import (
    CONVERT_PRESENTATION_TOPIC,
)


def test_curriculum_worker_is_disabled_unless_the_lms_enables_it(monkeypatch):
    monkeypatch.delenv("LMS_CURRICULUM_WORKER_ENABLED", raising=False)
    assert get_app_settings().worker.embedded_curriculum_enabled is False

    monkeypatch.setenv("LMS_CURRICULUM_WORKER_ENABLED", "true")
    assert get_app_settings().worker.embedded_curriculum_enabled is True


def test_embedded_curriculum_worker_claims_only_presentation_jobs(monkeypatch):
    settings = get_app_settings()
    captured: dict[str, object] = {}

    class _Thread:
        def __init__(self, *, target, kwargs, daemon, name):
            captured.update(
                target=target,
                kwargs=kwargs,
                daemon=daemon,
                name=name,
            )

        def start(self):
            captured["started"] = True

        def join(self, timeout):
            captured["join_timeout"] = timeout

        def is_alive(self):
            return False

    monkeypatch.setattr(curriculum_worker, "Thread", _Thread)
    handle = curriculum_worker.start_curriculum_worker(
        replace(
            settings,
            worker=replace(settings.worker, embedded_curriculum_enabled=True),
        )
    )
    embedded_container = captured["kwargs"]["container"]
    registry = captured["kwargs"]["registry"]

    assert captured["started"] is True
    assert captured["daemon"] is True
    assert captured["name"] == "lms-curriculum-worker"
    assert embedded_container.settings.worker.allowed_topics == (CONVERT_PRESENTATION_TOPIC,)
    assert registry.topics == (CONVERT_PRESENTATION_TOPIC,)

    handle.close()
    assert captured["join_timeout"] == 10


def test_lms_lifespan_owns_curriculum_worker_startup_and_shutdown(monkeypatch):
    settings = get_app_settings()
    settings = replace(
        settings,
        worker=replace(settings.worker, embedded_curriculum_enabled=True),
    )
    events: list[str] = []
    worker_handle = SimpleNamespace(close=lambda: events.append("worker_closed"))
    container = SimpleNamespace(close=lambda: events.append("container_closed"))
    app = SimpleNamespace(state=SimpleNamespace(settings=settings, container=container))

    monkeypatch.setattr(
        server,
        "start_curriculum_worker",
        lambda active_settings: (
            events.append(
                "worker_started" if active_settings is settings else "unexpected_settings"
            )
            or worker_handle
        ),
    )

    async def exercise_lifespan():
        async with server._lifespan(app):
            events.append("app_running")

    asyncio.run(exercise_lifespan())

    assert events == [
        "worker_started",
        "app_running",
        "worker_closed",
        "container_closed",
    ]
