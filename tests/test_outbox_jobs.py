"""Durable outbox and worker behavior without a live database."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from backend.core.clock import FixedClock
from backend.core.runtime.config import get_app_settings
from backend.modules.jobs import commands, repository
from backend.modules.jobs.domain_types import JobStatus
from backend.modules.jobs.schemas import EnqueueJobCommand, JobRecord


class _Rows:
    def __init__(self, rows=(), *, rowcount=0):
        self._rows = list(rows)
        self.rowcount = rowcount

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return self._rows


class _Connection:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def execute(self, sql, params=None):
        self.calls.append((sql, params))
        return self.results.pop(0)


class _UnitOfWork:
    def __init__(self, conn):
        self.conn = conn


def _job(*, attempts: int, max_attempts: int = 5) -> JobRecord:
    now = datetime(2026, 7, 26, tzinfo=UTC)
    return JobRecord(
        job_id=31,
        topic="example.created",
        payload={"candidate_id": 17},
        idempotency_key="example:17",
        status=JobStatus.RUNNING,
        attempts=attempts,
        max_attempts=max_attempts,
        available_at=now,
        lease_owner="worker-1",
        created_at=now,
    )


def test_enqueue_is_idempotent_and_returns_existing_job_id():
    conn = _Connection([_Rows(), _Rows([{"id": 44}])])

    job_id = repository.insert_job(
        conn,
        EnqueueJobCommand(
            topic="example.created",
            payload={"candidate_id": 17},
            idempotency_key="example:17",
        ),
    )

    assert job_id == 44
    assert "ON CONFLICT (idempotency_key) DO NOTHING" in conn.calls[0][0]
    assert "WHERE idempotency_key = %s" in conn.calls[1][0]


def test_claim_uses_skip_locked_and_a_bounded_lease():
    conn = _Connection([_Rows()])

    jobs = repository.claim_due_jobs(
        conn,
        worker_id="worker-1",
        limit=25,
        lease_seconds=300,
    )

    assert jobs == []
    sql, params = conn.calls[0]
    assert "FOR UPDATE SKIP LOCKED" in sql
    assert "lease_expires_at" in sql
    assert params == (25, "worker-1", 300)


def test_claim_can_be_restricted_to_an_exact_topic_allowlist():
    conn = _Connection([_Rows()])

    repository.claim_due_jobs(
        conn,
        worker_id="finance-worker",
        limit=10,
        lease_seconds=300,
        allowed_topics=(
            "finance.generate_invoices",
            "finance.send_billing_notification",
        ),
    )

    sql, params = conn.calls[0]
    assert "topic = ANY(%s::text[])" in sql
    assert params == (
        [
            "finance.generate_invoices",
            "finance.send_billing_notification",
        ],
        10,
        "finance-worker",
        300,
    )


def test_failure_retries_with_exponential_backoff(monkeypatch):
    captured = {}

    def record_failure(_conn, **values):
        captured.update(values)
        return True

    monkeypatch.setattr(repository, "record_job_failure", record_failure)
    now = datetime(2026, 7, 26, 8, 0, tzinfo=UTC)
    settings = get_app_settings().worker

    saved = commands.fail_job(
        _UnitOfWork(object()),
        job=_job(attempts=3),
        worker_id="worker-1",
        error=RuntimeError("temporary\nnetwork failure"),
        settings=settings,
        clock=FixedClock(now),
    )

    assert saved is True
    assert captured["is_dead"] is False
    assert captured["error_summary"] == "temporary network failure"
    assert captured["next_available_at"] == now + timedelta(seconds=settings.retry_base_seconds * 4)


def test_last_attempt_moves_job_to_dead_state(monkeypatch):
    captured = {}

    def record_failure(_conn, **values):
        captured.update(values)
        return True

    monkeypatch.setattr(repository, "record_job_failure", record_failure)

    commands.fail_job(
        _UnitOfWork(object()),
        job=_job(attempts=5),
        worker_id="worker-1",
        error=RuntimeError("permanent"),
        settings=get_app_settings().worker,
        clock=FixedClock(datetime(2026, 7, 26, tzinfo=UTC)),
    )

    assert captured["is_dead"] is True


def test_dead_job_replay_resets_delivery_state():
    conn = _Connection([_Rows(rowcount=1)])

    assert repository.replay_dead_job(conn, job_id=31) is True
    sql, params = conn.calls[0]
    assert "attempts = 0" in sql
    assert "status = 'dead'" in sql
    assert params == (31,)


def test_expired_final_lease_moves_job_to_dead_instead_of_retry_loop():
    conn = _Connection([_Rows(rowcount=1)])

    assert repository.release_expired_leases(conn) == 1
    sql, _params = conn.calls[0]
    assert "WHEN attempts >= max_attempts THEN 'dead'" in sql
    assert "WHEN attempts >= max_attempts THEN now()" in sql


def test_expired_lease_recovery_uses_the_same_topic_allowlist():
    conn = _Connection([_Rows(rowcount=1)])

    repository.release_expired_leases(
        conn,
        allowed_topics=("finance.generate_invoices",),
    )

    sql, params = conn.calls[0]
    assert "topic = ANY(%s::text[])" in sql
    assert params == (["finance.generate_invoices"],)


def test_migration_and_process_entrypoint_define_the_durable_worker():
    migration = Path("database/alembic/versions/0043_outbox_jobs.py").read_text(encoding="utf-8")
    repository_source = Path("backend/modules/jobs/repository.py").read_text(encoding="utf-8")
    procfile = Path("Procfile").read_text(encoding="utf-8")

    assert "GENERATED ALWAYS AS IDENTITY" in migration
    assert "idempotency_key" in migration
    assert "lease_expires_at" in migration
    assert "FOR UPDATE SKIP LOCKED" in repository_source
    assert "worker: python main.py worker" in procfile
