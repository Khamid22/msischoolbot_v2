"""Real PostgreSQL syntax and mapping checks for the Teacher Support directory."""

from __future__ import annotations

import os

import pytest

from backend.modules.domains.teacher_records import support_repository


def _test_database_url() -> str:
    return os.environ.get("MSI_TEST_DATABASE_URL", "").strip()


@pytest.mark.postgres
def test_teacher_support_queries_run_in_a_read_only_postgres_transaction():
    database_url = _test_database_url()
    if not database_url:
        pytest.skip("Set MSI_TEST_DATABASE_URL to run PostgreSQL integration tests.")

    psycopg = pytest.importorskip("psycopg")
    from psycopg.rows import dict_row

    connection = psycopg.connect(database_url, row_factory=dict_row)
    try:
        database_name = str(
            connection.execute("SELECT current_database() AS name").fetchone()["name"]
        )
        if "test" not in database_name.casefold():
            pytest.fail("MSI_TEST_DATABASE_URL must point to a database containing 'test'.")

        connection.execute("SET TRANSACTION READ ONLY")
        rows = support_repository.search_teacher_support_rows(
            connection,
            search_text="",
            status="all",
            selected_school_id=None,
            allowed_school_ids=(),
            all_schools=True,
            cursor_name="",
            cursor_id=0,
            limit=2,
        )
        if rows:
            teacher = support_repository.get_teacher_support_row(
                connection,
                teacher_id=int(rows[0]["teacher_id"]),
                allowed_school_ids=(),
                all_schools=True,
            )
            assert teacher
            assert int(teacher["teacher_id"]) == int(rows[0]["teacher_id"])
    finally:
        connection.rollback()
        connection.close()
