"""Real PostgreSQL transaction and concurrency tests for the durable outbox."""

from __future__ import annotations

import os
import uuid
from collections.abc import Callable, Iterator

import pytest

from backend.modules.jobs import repository
from backend.modules.jobs.schemas import EnqueueJobCommand

PostgresConnectionFactory = Callable[[], object]


def _test_database_url() -> str:
    return os.environ.get("MSI_TEST_DATABASE_URL", "").strip()


@pytest.fixture
def postgres_outbox() -> Iterator[tuple[PostgresConnectionFactory, str]]:
    database_url = _test_database_url()
    if not database_url:
        pytest.skip("Set MSI_TEST_DATABASE_URL to run PostgreSQL integration tests.")

    psycopg = pytest.importorskip("psycopg")
    from psycopg.rows import dict_row

    def connect():
        return psycopg.connect(database_url, row_factory=dict_row)

    safety_connection = connect()
    database_name = str(
        safety_connection.execute("SELECT current_database() AS database_name").fetchone()[
            "database_name"
        ]
    )
    table_name = safety_connection.execute(
        "SELECT to_regclass('msi_v2.outbox_jobs') AS table_name"
    ).fetchone()["table_name"]
    safety_connection.close()
    if "test" not in database_name.casefold():
        pytest.fail("MSI_TEST_DATABASE_URL must point to a database containing 'test'.")
    if not table_name:
        pytest.fail("Run `alembic upgrade head` on MSI_TEST_DATABASE_URL first.")

    key_prefix = f"pytest-outbox:{uuid.uuid4().hex}"
    try:
        yield connect, key_prefix
    finally:
        cleanup_connection = connect()
        cleanup_connection.execute(
            "DELETE FROM msi_v2.outbox_jobs WHERE idempotency_key LIKE %s",
            (f"{key_prefix}:%",),
        )
        cleanup_connection.commit()
        cleanup_connection.close()


def _command(key_prefix: str, suffix: str) -> EnqueueJobCommand:
    return EnqueueJobCommand(
        topic="test.example",
        payload={"suffix": suffix},
        idempotency_key=f"{key_prefix}:{suffix}",
    )


@pytest.mark.postgres
def test_outbox_insert_obeys_commit_visibility(postgres_outbox):
    connect, key_prefix = postgres_outbox
    writer = connect()
    reader = connect()
    try:
        job_id = repository.insert_job(writer, _command(key_prefix, "commit"))
        before_commit = reader.execute(
            "SELECT count(*) AS count FROM msi_v2.outbox_jobs WHERE id = %s",
            (job_id,),
        ).fetchone()
        assert int(before_commit["count"]) == 0

        writer.commit()
        after_commit = reader.execute(
            "SELECT count(*) AS count FROM msi_v2.outbox_jobs WHERE id = %s",
            (job_id,),
        ).fetchone()
        assert int(after_commit["count"]) == 1
    finally:
        writer.close()
        reader.close()


@pytest.mark.postgres
def test_outbox_insert_rolls_back_with_its_command(postgres_outbox):
    connect, key_prefix = postgres_outbox
    writer = connect()
    verifier = connect()
    try:
        job_id = repository.insert_job(writer, _command(key_prefix, "rollback"))
        writer.rollback()
        stored = verifier.execute(
            "SELECT count(*) AS count FROM msi_v2.outbox_jobs WHERE id = %s",
            (job_id,),
        ).fetchone()
        assert int(stored["count"]) == 0
    finally:
        writer.close()
        verifier.close()


@pytest.mark.postgres
def test_competing_workers_skip_each_others_locked_jobs(postgres_outbox):
    connect, key_prefix = postgres_outbox
    setup_connection = connect()
    first_worker = connect()
    second_worker = connect()
    try:
        repository.insert_job(setup_connection, _command(key_prefix, "first"))
        repository.insert_job(setup_connection, _command(key_prefix, "second"))
        setup_connection.commit()

        first_claim = repository.claim_due_jobs(
            first_worker,
            worker_id="pytest-worker-1",
            limit=1,
            lease_seconds=60,
        )
        second_claim = repository.claim_due_jobs(
            second_worker,
            worker_id="pytest-worker-2",
            limit=2,
            lease_seconds=60,
        )

        assert len(first_claim) == 1
        assert len(second_claim) == 1
        assert first_claim[0].job_id != second_claim[0].job_id
    finally:
        first_worker.rollback()
        second_worker.rollback()
        setup_connection.close()
        first_worker.close()
        second_worker.close()
