"""Recruitment notification delivery process contracts."""

from pathlib import Path


def test_recruitment_telegram_worker_is_retired():
    procfile = Path("Procfile").read_text()
    main_source = Path("main.py").read_text()

    assert "worker: python main.py worker" not in procfile
    assert '"recruitment-worker": "worker"' not in main_source
    assert "process_due_notifications" not in main_source
    assert not Path("backend/modules/hr/recruitment/worker.py").exists()
