"""Read-only durable-job use cases."""

from backend.core.unit_of_work import UnitOfWork
from backend.modules.jobs import repository
from backend.modules.jobs.schemas import JobRecord


def find_job(uow: UnitOfWork, job_id: int) -> JobRecord | None:
    return repository.find_job(uow.conn, job_id)


__all__ = ["find_job"]
