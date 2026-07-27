"""Public typed durable-job contracts."""

from __future__ import annotations

from typing import Protocol

from backend.core.jobs import DurableJobCommand
from backend.core.unit_of_work import Connection
from backend.modules.jobs import repository
from backend.modules.jobs.schemas import EnqueueJobCommand


class TransactionContext(Protocol):
    @property
    def conn(self) -> Connection: ...


def enqueue_job(transaction: TransactionContext, command: DurableJobCommand) -> int:
    if not isinstance(command, EnqueueJobCommand):
        raise TypeError("UnitOfWork.enqueue requires an EnqueueJobCommand.")
    return repository.insert_job(transaction.conn, command)


def enqueue_on_connection(conn: Connection, command: DurableJobCommand) -> int:
    if not isinstance(command, EnqueueJobCommand):
        raise TypeError("UnitOfWork.enqueue requires an EnqueueJobCommand.")
    return repository.insert_job(conn, command)


__all__ = ["TransactionContext", "enqueue_job", "enqueue_on_connection"]
