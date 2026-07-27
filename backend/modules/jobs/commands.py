"""Transactional durable-job commands."""

from __future__ import annotations

from datetime import timedelta

from backend.core.clock import Clock
from backend.core.runtime.config import WorkerSettings
from backend.core.unit_of_work import UnitOfWork
from backend.modules.jobs import repository
from backend.modules.jobs.schemas import EnqueueJobCommand, JobRecord


def enqueue_job(uow: UnitOfWork, command: EnqueueJobCommand) -> int:
    return repository.insert_job(uow.conn, command)


def claim_jobs(
    uow: UnitOfWork,
    *,
    worker_id: str,
    settings: WorkerSettings,
) -> list[JobRecord]:
    repository.release_expired_leases(uow.conn)
    return repository.claim_due_jobs(
        uow.conn,
        worker_id=worker_id,
        limit=settings.batch_size,
        lease_seconds=settings.lease_seconds,
    )


def complete_job(uow: UnitOfWork, *, job_id: int, worker_id: str) -> bool:
    return repository.complete_job(uow.conn, job_id=job_id, worker_id=worker_id)


def replay_dead_job(uow: UnitOfWork, *, job_id: int) -> bool:
    """Reset an inspected dead job so an operator can safely replay it."""

    return repository.replay_dead_job(uow.conn, job_id=job_id)


def fail_job(
    uow: UnitOfWork,
    *,
    job: JobRecord,
    worker_id: str,
    error: Exception,
    settings: WorkerSettings,
    clock: Clock,
) -> bool:
    is_dead = job.attempts >= job.max_attempts
    delay_seconds = min(
        settings.retry_base_seconds * (2 ** max(0, job.attempts - 1)),
        settings.retry_max_seconds,
    )
    error_summary = " ".join(str(error).splitlines()).strip()[:2000]
    return repository.record_job_failure(
        uow.conn,
        job_id=job.job_id,
        worker_id=worker_id,
        next_available_at=clock.now() + timedelta(seconds=delay_seconds),
        error_summary=error_summary or type(error).__name__,
        is_dead=is_dead,
    )


__all__ = [
    "claim_jobs",
    "complete_job",
    "enqueue_job",
    "fail_job",
    "replay_dead_job",
]
