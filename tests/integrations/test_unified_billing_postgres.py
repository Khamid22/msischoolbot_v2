"""Disposable PostgreSQL transaction checks for the unified Finance ledger."""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from backend.modules.domains.finance.commands import (
    BillingActor,
    issue_student_invoice,
    record_manual_payment,
)
from backend.modules.domains.finance.domain_types import (
    InvoiceKind,
    ManualPaymentMethod,
)
from backend.modules.domains.finance.queries import BillingSchoolScope
from backend.modules.domains.finance.schemas import (
    IssueStudentInvoiceCommand,
    RecordManualInvoicePaymentCommand,
)
from tests.integrations.test_parent_support_postgres import _connect_test_database


def _active_student_enrollment(connection):
    existing = connection.execute(
        """
        SELECT student.id AS student_id, student.version,
               subject.id AS subject_id
        FROM msi_v2.students student
        JOIN msi_v2.group_students enrollment
          ON enrollment.student_id = student.id
         AND enrollment.enrollment_status = 'active'
        JOIN msi_v2.groups group_row ON group_row.id = enrollment.group_id
        JOIN msi_v2.subject_programs program ON program.id = group_row.program_id
        JOIN msi_v2.subjects subject ON subject.id = program.subject_id
        WHERE student.status = 'active'
        ORDER BY student.id, enrollment.group_id
        LIMIT 1
        """
    ).fetchone()
    if existing:
        return existing

    suffix = uuid4().hex[:10]
    school = connection.execute(
        """
        INSERT INTO msi_v2.schools (school_key, school_name)
        VALUES (%s, %s)
        RETURNING id
        """,
        (f"billing-test-{suffix}", "Billing Integration School"),
    ).fetchone()
    subject = connection.execute(
        """
        INSERT INTO msi_v2.subjects (subject_key, subject_name)
        VALUES (%s, %s)
        RETURNING id
        """,
        (f"billing-subject-{suffix}", "Billing Integration Subject"),
    ).fetchone()
    program = connection.execute(
        """
        INSERT INTO msi_v2.subject_programs (
            subject_id, academic_year, program_name
        )
        VALUES (%s, %s, %s)
        RETURNING id
        """,
        (subject["id"], f"test-{suffix}", "Billing Integration Program"),
    ).fetchone()
    group_row = connection.execute(
        """
        INSERT INTO msi_v2.groups (
            school_id, program_id, group_name, group_code
        )
        VALUES (%s, %s, %s, %s)
        RETURNING id
        """,
        (
            school["id"],
            program["id"],
            "Billing Integration Group",
            f"BT-{suffix}",
        ),
    ).fetchone()
    student = connection.execute(
        """
        INSERT INTO msi_v2.students (
            student_code, full_name, school_id, legacy_student_row_id
        )
        VALUES (%s, %s, %s, %s)
        RETURNING id, version
        """,
        (
            f"BT-{suffix}",
            "Billing Integration Student",
            school["id"],
            int(f"8{int(suffix[:8], 16):09d}"),
        ),
    ).fetchone()
    connection.execute(
        """
        INSERT INTO msi_v2.group_students (group_id, student_id)
        VALUES (%s, %s)
        """,
        (group_row["id"], student["id"]),
    )
    return {
        "student_id": student["id"],
        "version": student["version"],
        "subject_id": subject["id"],
    }


@pytest.mark.postgres
def test_current_invoice_and_manual_settlement_roll_back_atomically():
    connection = _connect_test_database()
    invoice_number = ""
    try:
        if connection.execute(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'msi_v2'
              AND table_name = 'invoices'
              AND column_name = 'origin'
            """
        ).fetchone() is None:
            pytest.fail("Run `alembic upgrade head` on MSI_TEST_DATABASE_URL first.")
        enrollment = _active_student_enrollment(connection)
        if enrollment is None:
            pytest.skip("The PostgreSQL test database has no active student enrollment.")

        invoice = issue_student_invoice(
            connection,
            IssueStudentInvoiceCommand(
                student_id=int(enrollment["student_id"]),
                subject_id=int(enrollment["subject_id"]),
                description="Rollback integration invoice",
                amount_minor=10_000,
                due_date=date.today(),
                billing_period=date.today().replace(day=1),
                invoice_kind=InvoiceKind.MANUAL,
                expected_student_version=int(enrollment["version"]),
            ),
            actor=BillingActor(staff_id=None, account_id=None),
            scope=BillingSchoolScope(all_schools=True),
        )
        invoice_number = invoice.invoice_number
        settled = record_manual_payment(
            connection,
            invoice.invoice_id,
            RecordManualInvoicePaymentCommand(
                amount_minor=10_000,
                method=ManualPaymentMethod.CASH,
                paid_at=datetime.now(UTC),
                reference="rollback-integration",
                reason="Verify one-transaction settlement.",
                expected_version=invoice.version,
            ),
            actor=BillingActor(staff_id=None, account_id=None),
            scope=BillingSchoolScope(all_schools=True),
        )
        assert settled.status.value == "paid"
        assert settled.balance_minor == 0
    finally:
        connection.rollback()
        if invoice_number:
            assert connection.execute(
                "SELECT id FROM msi_v2.invoices WHERE invoice_number = %s",
                (invoice_number,),
            ).fetchone() is None
            connection.rollback()
        connection.close()
