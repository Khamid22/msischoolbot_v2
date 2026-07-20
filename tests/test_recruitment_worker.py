"""Dedicated Recruitment worker contracts."""

from __future__ import annotations

import threading
from pathlib import Path

from backend.modules.hr.recruitment import worker


def test_worker_is_not_started_by_the_web_process():
    server_source = Path("backend/server.py").read_text()
    procfile = Path("Procfile").read_text()

    assert "process_due_notifications" not in server_source
    assert "recruitment_notification_worker" not in server_source
    assert "worker: python main.py worker" in procfile


def test_worker_processes_one_bounded_batch(monkeypatch):
    monkeypatch.setenv("RECRUITMENT_NOTIFICATION_BATCH_LIMIT", "17")
    calls: list[int] = []

    delivered = worker.run_once(
        processor=lambda *, limit: calls.append(limit) or 4,
    )

    assert delivered == 4
    assert calls == [17]


def test_worker_loop_can_stop_without_sleeping_forever(monkeypatch):
    monkeypatch.setenv("RECRUITMENT_NOTIFICATION_POLL_SECONDS", "5")
    stop_event = threading.Event()
    calls: list[int] = []

    def process(*, limit: int) -> int:
        calls.append(limit)
        stop_event.set()
        return 0

    worker.run_forever(stop_event=stop_event, processor=process)

    assert calls == [25]
