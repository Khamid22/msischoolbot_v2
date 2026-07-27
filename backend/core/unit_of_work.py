"""Explicit PostgreSQL transaction ownership for command and query handlers."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol, Self

from backend.core.database import connect_auth_db
from backend.core.jobs import DurableJobCommand


class Connection(Protocol):
    def execute(self, sql: str, params: object = None) -> Any: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...

    def close(self) -> None: ...


ConnectionFactory = Callable[[], Connection]
JobEnqueuer = Callable[[Connection, DurableJobCommand], int]


class UnitOfWork:
    """One explicit connection and transaction.

    Exiting without ``commit`` rolls back, which prevents accidental partial
    writes when a command returns early.
    """

    def __init__(
        self,
        connection_factory: ConnectionFactory = connect_auth_db,
        *,
        read_only: bool = False,
        job_enqueuer: JobEnqueuer | None = None,
    ) -> None:
        self._connection_factory = connection_factory
        self._read_only = read_only
        self._job_enqueuer = job_enqueuer
        self._connection: Connection | None = None
        self._is_complete = False
        self._has_entered = False

    @property
    def conn(self) -> Connection:
        if self._connection is None:
            raise RuntimeError("UnitOfWork must be entered before its connection is used.")
        return self._connection

    @property
    def is_read_only(self) -> bool:
        return self._read_only

    def __enter__(self) -> Self:
        if self._has_entered:
            raise RuntimeError("UnitOfWork instances cannot be re-entered.")
        self._has_entered = True
        self._connection = self._connection_factory()
        if self._read_only:
            self._connection.execute("SET TRANSACTION READ ONLY")
        return self

    def commit(self) -> None:
        if self._read_only:
            raise RuntimeError("A read-only UnitOfWork cannot commit.")
        if self._is_complete:
            raise RuntimeError("This UnitOfWork transaction is already complete.")
        self.conn.commit()
        self._is_complete = True

    def rollback(self) -> None:
        if self._is_complete:
            raise RuntimeError("This UnitOfWork transaction is already complete.")
        self.conn.rollback()
        self._is_complete = True

    def enqueue(self, command: DurableJobCommand) -> int:
        """Enqueue a typed outbox command in this transaction."""

        if self._read_only:
            raise RuntimeError("A read-only UnitOfWork cannot enqueue jobs.")
        if self._job_enqueuer is None:
            raise RuntimeError("No durable-job enqueuer is configured for this UnitOfWork.")
        return self._job_enqueuer(self.conn, command)

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if self._connection is None:
            return
        try:
            if not self._is_complete:
                self._connection.rollback()
                self._is_complete = True
        finally:
            self._connection.close()
            self._connection = None


class UnitOfWorkFactory:
    def __init__(
        self,
        connection_factory: ConnectionFactory = connect_auth_db,
        *,
        job_enqueuer: JobEnqueuer | None = None,
    ) -> None:
        self._connection_factory = connection_factory
        self._job_enqueuer = job_enqueuer

    def transaction(self) -> UnitOfWork:
        return UnitOfWork(
            self._connection_factory,
            job_enqueuer=self._job_enqueuer,
        )

    def read(self) -> UnitOfWork:
        return UnitOfWork(
            self._connection_factory,
            read_only=True,
            job_enqueuer=self._job_enqueuer,
        )


def commit_unit_of_work(unit_of_work: UnitOfWork) -> None:
    """Complete a person-orchestrated write without exposing commit calls there."""

    unit_of_work.commit()


__all__ = [
    "Connection",
    "ConnectionFactory",
    "commit_unit_of_work",
    "JobEnqueuer",
    "UnitOfWork",
    "UnitOfWorkFactory",
]
