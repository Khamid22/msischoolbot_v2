"""Standalone durable PostgreSQL worker entrypoint."""

from __future__ import annotations

import logging
import os
import socket
from threading import Event

from backend.application.container import AppContainer
from backend.application.modules import build_job_handler_registry
from backend.core.jobs import JobExecutionContext
from backend.modules.jobs import commands
from backend.modules.jobs.handlers import JobHandlerRegistry
from backend.modules.jobs.schemas import JobRecord

LOGGER = logging.getLogger("msi.worker")


def default_worker_id() -> str:
    return f"{socket.gethostname()}:{os.getpid()}"


def _record_success(container: AppContainer, job: JobRecord, worker_id: str) -> None:
    with container.unit_of_work_factory.transaction() as uow:
        if not commands.complete_job(uow, job_id=job.job_id, worker_id=worker_id):
            raise RuntimeError(f"Worker lease was lost for job {job.job_id}.")
        uow.commit()


def _record_failure(
    container: AppContainer,
    job: JobRecord,
    worker_id: str,
    error: Exception,
) -> None:
    with container.unit_of_work_factory.transaction() as uow:
        commands.fail_job(
            uow,
            job=job,
            worker_id=worker_id,
            error=error,
            settings=container.settings.worker,
            clock=container.clock,
        )
        uow.commit()


def _execute_job(
    container: AppContainer,
    registry: JobHandlerRegistry,
    job: JobRecord,
    worker_id: str,
) -> None:
    handler = registry.handler_for(job.topic)
    if handler is None:
        _record_failure(
            container,
            job,
            worker_id,
            RuntimeError(f"No handler is registered for job topic {job.topic!r}."),
        )
        return
    context = JobExecutionContext(
        job_id=job.job_id,
        attempt=job.attempts,
        worker_id=worker_id,
    )
    try:
        handler.handle(job.payload, context)
    except Exception as exc:
        LOGGER.exception(
            "job_failed job_id=%s topic=%s attempt=%s",
            job.job_id,
            job.topic,
            job.attempts,
        )
        _record_failure(container, job, worker_id, exc)
        return
    _record_success(container, job, worker_id)


def run_worker_once(
    container: AppContainer,
    registry: JobHandlerRegistry,
    *,
    worker_id: str | None = None,
) -> int:
    active_worker_id = worker_id or container.settings.worker.worker_id or default_worker_id()
    with container.unit_of_work_factory.transaction() as uow:
        jobs = commands.claim_jobs(
            uow,
            worker_id=active_worker_id,
            settings=container.settings.worker,
        )
        uow.commit()
    for job in jobs:
        _execute_job(container, registry, job, active_worker_id)
    return len(jobs)


def run_worker(
    *,
    container: AppContainer | None = None,
    registry: JobHandlerRegistry | None = None,
    stop_event: Event | None = None,
) -> None:
    active_container = container or AppContainer.build()
    active_registry = registry or build_job_handler_registry()
    shutdown = stop_event or Event()
    worker_id = active_container.settings.worker.worker_id or default_worker_id()
    LOGGER.info(
        "worker_started worker_id=%s topics=%s",
        worker_id,
        ",".join(active_registry.topics) or "(none)",
    )
    try:
        while not shutdown.is_set():
            claimed = run_worker_once(
                active_container,
                active_registry,
                worker_id=worker_id,
            )
            if not claimed:
                shutdown.wait(active_container.settings.worker.poll_interval_seconds)
    finally:
        active_container.close()
        LOGGER.info("worker_stopped worker_id=%s", worker_id)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    try:
        run_worker()
    except KeyboardInterrupt:
        LOGGER.info("worker_interrupted")


if __name__ == "__main__":
    main()


__all__ = ["default_worker_id", "main", "run_worker", "run_worker_once"]
