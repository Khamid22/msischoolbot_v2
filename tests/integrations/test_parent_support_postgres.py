"""Disposable PostgreSQL checks for parent payments and support tickets."""

from __future__ import annotations

import os

import pytest

from backend.modules.domains.finance import repository as finance_repository
from backend.modules.domains.support_cases.tickets import repository as ticket_repository
from backend.modules.domains.support_cases.tickets.contracts import (
    TicketCategory,
    create_parent_ticket,
    reply_to_parent_ticket,
)


def _test_database_url() -> str:
    return os.environ.get("MSI_TEST_DATABASE_URL", "").strip()


def _connect_test_database():
    database_url = _test_database_url()
    if not database_url:
        pytest.skip("Set MSI_TEST_DATABASE_URL to run PostgreSQL integration tests.")

    psycopg = pytest.importorskip("psycopg")
    from psycopg.rows import dict_row

    connection = psycopg.connect(database_url, row_factory=dict_row)
    database_name = str(
        connection.execute("SELECT current_database() AS name").fetchone()["name"]
    )
    if "test" not in database_name.casefold():
        connection.close()
        pytest.fail("MSI_TEST_DATABASE_URL must point to a database containing 'test'.")
    return connection


def _linked_parent_and_student(connection):
    return connection.execute(
        """
        SELECT link.parent_id, st.legacy_student_row_id
        FROM msi_v2.parent_student_links link
        JOIN msi_v2.students st ON st.id = link.student_id
        JOIN msi_v2.parents parent ON parent.id = link.parent_id
        WHERE link.status = 'active'
          AND parent.status = 'active'
          AND st.legacy_student_row_id IS NOT NULL
        ORDER BY link.id
        LIMIT 1
        """
    ).fetchone()


@pytest.mark.postgres
def test_parent_payment_and_ticket_queries_run_in_read_only_postgres():
    connection = _connect_test_database()
    try:
        connection.execute("SET TRANSACTION READ ONLY")
        linked_student = _linked_parent_and_student(connection)
        if linked_student:
            finance_repository.list_student_payment_rows(
                connection,
                int(linked_student["legacy_student_row_id"]),
            )

        rows = ticket_repository.list_support_ticket_rows(
            connection,
            search_text="",
            selected_school_id=None,
            allowed_school_ids=(),
            all_schools=True,
            status="",
            category="",
            assigned_staff_id=None,
            is_unassigned=False,
            cursor_status_rank=-1,
            cursor_updated_at="",
            cursor_id=0,
            limit=2,
        )
        assert len(rows) <= 2
    finally:
        connection.rollback()
        connection.close()


@pytest.mark.postgres
def test_parent_ticket_creation_reply_and_rollback_are_atomic():
    connection = _connect_test_database()
    ticket_id = 0
    try:
        linked = _linked_parent_and_student(connection)
        if linked is None:
            pytest.skip("The PostgreSQL test database has no active parent-child link.")

        ticket = create_parent_ticket(
            connection,
            parent_id=int(linked["parent_id"]),
            student_row_id=int(linked["legacy_student_row_id"]),
            category=TicketCategory.ATTENDANCE,
            topic="Rollback integration check",
            message="Opening message created in the same transaction.",
        )
        ticket_id = ticket.ticket_id
        assert [message.author_type for message in ticket.messages] == ["parent"]

        replied = reply_to_parent_ticket(
            connection,
            parent_id=int(linked["parent_id"]),
            ticket_id=ticket_id,
            body="A second parent message before rollback.",
        )
        assert len(replied.messages) == 2
    finally:
        connection.rollback()
        if ticket_id:
            assert connection.execute(
                "SELECT id FROM msi_v2.support_tickets WHERE id = %s",
                (ticket_id,),
            ).fetchone() is None
            connection.rollback()
        connection.close()


@pytest.mark.postgres
def test_support_ticket_row_lock_rejects_a_competing_writer():
    psycopg = pytest.importorskip("psycopg")
    first = _connect_test_database()
    second = _connect_test_database()
    try:
        ticket = first.execute(
            "SELECT id FROM msi_v2.support_tickets ORDER BY id LIMIT 1"
        ).fetchone()
        if ticket is None:
            pytest.skip("The PostgreSQL test database has no support ticket to lock.")

        ticket_id = int(ticket["id"])
        ticket_repository.get_ticket_row(first, ticket_id=ticket_id, for_update=True)
        second.execute("SET LOCAL lock_timeout = '250ms'")
        with pytest.raises(psycopg.errors.LockNotAvailable):
            ticket_repository.get_ticket_row(
                second,
                ticket_id=ticket_id,
                for_update=True,
            )
    finally:
        first.rollback()
        second.rollback()
        first.close()
        second.close()
