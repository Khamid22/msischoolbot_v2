"""Durable worker process contracts."""

from pathlib import Path


def test_generic_postgresql_worker_replaces_the_retired_recruitment_worker():
    procfile = Path("Procfile").read_text()
    main_source = Path("main.py").read_text()
    worker_source = Path("backend/application/worker.py").read_text()
    repository_source = Path("backend/modules/jobs/repository.py").read_text()

    assert "worker: python main.py worker" in procfile
    assert '"recruitment-worker": "worker"' in main_source
    assert "run_worker()" in main_source
    assert "build_job_handler_registry" in worker_source
    assert "FOR UPDATE SKIP LOCKED" in repository_source
    assert "process_due_notifications" not in main_source
    assert not Path("backend/modules/domains/recruitment/worker.py").exists()
