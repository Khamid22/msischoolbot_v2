"""Disposable PostgreSQL transaction checks for the unified Finance ledger."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest

from backend.modules.domains.finance import billing_profile_repository
from backend.modules.domains.finance.billing_cycles import plan_billing_cycles
from backend.modules.domains.finance.commands import (
    BillingActor,
    configure_billing_profile,
    issue_student_invoice,
    record_manual_payment,
)
from backend.modules.domains.finance.domain_types import (
    BillingAccountType,
    BillingPricingMode,
    BillingProfileStatus,
    BillingScheduleApplyTo,
    InvoiceKind,
    ManualPaymentMethod,
)
from backend.modules.domains.finance.queries import (
    BillingSchoolScope,
    get_billing_account,
    get_billing_automation_status,
    list_billing_accounts,
)
from backend.modules.domains.finance.schemas import (
    ConfigureBillingProfileCommand,
    IssueStudentInvoiceCommand,
    RecordManualInvoicePaymentCommand,
)
from tests.integrations.test_parent_support_postgres import _connect_test_database


def _active_student_enrollment(connection):
    existing = connection.execute(
        """
        SELECT student.id AS student_id, student.version,
               student.school_id, enrollment.group_id, subject.id AS subject_id
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
        "school_id": school["id"],
        "group_id": group_row["id"],
        "subject_id": subject["id"],
    }


@pytest.mark.postgres
def test_current_invoice_and_manual_settlement_roll_back_atomically():
    connection = _connect_test_database()
    invoice_number = ""
    try:
        if (
            connection.execute(
                """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'msi_v2'
              AND table_name = 'invoices'
              AND column_name = 'origin'
            """
            ).fetchone()
            is None
        ):
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
            assert (
                connection.execute(
                    "SELECT id FROM msi_v2.invoices WHERE invoice_number = %s",
                    (invoice_number,),
                ).fetchone()
                is None
            )
            connection.rollback()
        connection.close()


@pytest.mark.postgres
def test_same_day_billing_profile_resave_preserves_valid_history():
    connection = _connect_test_database()
    try:
        enrollment = _active_student_enrollment(connection)
        effective_date = date(2026, 8, 1)
        profile_id = billing_profile_repository.upsert_billing_profile(
            connection,
            student_id=int(enrollment["student_id"]),
            school_id=int(enrollment["school_id"]),
            billing_parent_id=None,
            billing_day=1,
            starts_on=effective_date,
            status=BillingProfileStatus.ACTIVE,
            expected_version=None,
            staff_id=None,
        )
        assert profile_id > 0
        item = (
            int(enrollment["group_id"]),
            int(enrollment["subject_id"]),
            "Billing Integration Subject",
            20_000,
        )
        billing_profile_repository.replace_billing_items(
            connection,
            profile_id=profile_id,
            starts_on=effective_date,
            items=[item],
            staff_id=None,
        )
        updated_profile_id = billing_profile_repository.upsert_billing_profile(
            connection,
            student_id=int(enrollment["student_id"]),
            school_id=int(enrollment["school_id"]),
            billing_parent_id=None,
            billing_day=1,
            starts_on=effective_date,
            status=BillingProfileStatus.ACTIVE,
            expected_version=1,
            staff_id=None,
        )
        assert updated_profile_id == profile_id
        billing_profile_repository.replace_billing_items(
            connection,
            profile_id=profile_id,
            starts_on=effective_date,
            items=[(*item[:3], 25_000)],
            staff_id=None,
        )

        rows = connection.execute(
            """
            SELECT status, active_from, active_until, amount_minor, cancelled_at
            FROM msi_v2.student_billing_items
            WHERE profile_id = %s
            ORDER BY id
            """,
            (profile_id,),
        ).fetchall()
        assert len(rows) == 1
        assert rows[0]["status"] == "active"
        assert rows[0]["active_from"] == effective_date
        assert rows[0]["active_until"] is None
        assert rows[0]["amount_minor"] == 25_000
        assert rows[0]["cancelled_at"] is None
    finally:
        connection.rollback()
        connection.close()


@pytest.mark.postgres
def test_first_total_schedule_issues_one_live_invoice_and_enforcement_window():
    connection = _connect_test_database()
    try:
        enrollment = _active_student_enrollment(connection)
        command = ConfigureBillingProfileCommand(
            student_id=int(enrollment["student_id"]),
            billing_day=1,
            pricing_mode=BillingPricingMode.TOTAL,
            total_amount_minor=2_000_000_00,
            apply_to=BillingScheduleApplyTo.CURRENT_CYCLE,
        )
        profile = configure_billing_profile(
            connection,
            command,
            actor=BillingActor(staff_id=None, account_id=None),
            scope=BillingSchoolScope(all_schools=True),
        )
        repeated = configure_billing_profile(
            connection,
            command.model_copy(update={"expected_version": profile.version}),
            actor=BillingActor(staff_id=None, account_id=None),
            scope=BillingSchoolScope(all_schools=True),
        )

        live = connection.execute(
            """
            SELECT cycle.id AS cycle_id, cycle.revision, cycle.pricing_mode,
                   cycle.due_at,
                   invoice.id AS invoice_id, invoice.total_minor,
                   invoice.issued_at, schedule.id AS schedule_id,
                   schedule.countdown_started_at, schedule.deadline_at
            FROM msi_v2.student_billing_cycles cycle
            JOIN msi_v2.invoices invoice ON invoice.billing_cycle_id = cycle.id
            JOIN msi_v2.invoice_enforcement_schedules schedule
              ON schedule.invoice_id = invoice.id
            WHERE cycle.student_id = %s
              AND cycle.state = 'invoiced'
              AND invoice.status <> 'voided'
            """,
            (int(enrollment["student_id"]),),
        ).fetchone()
        assert live is not None
        assert live["revision"] == 1
        assert live["pricing_mode"] == "total"
        assert live["total_minor"] == 2_000_000_00
        assert live["due_at"] == live["deadline_at"]
        assert live["deadline_at"] - live["countdown_started_at"] == timedelta(hours=48)
        assert abs((live["issued_at"] - live["countdown_started_at"]).total_seconds()) < 10
        assert (
            connection.execute(
                """
            SELECT count(*) AS count
            FROM msi_v2.invoice_lines
            WHERE invoice_id = %s AND description = 'Monthly tuition'
            """,
                (int(live["invoice_id"]),),
            ).fetchone()["count"]
            == 1
        )
        assert (
            connection.execute(
                """
            SELECT count(*) AS count
            FROM msi_v2.student_billing_cycle_coverage
            WHERE cycle_id = %s
            """,
                (int(live["cycle_id"]),),
            ).fetchone()["count"]
            >= 1
        )
        assert (
            connection.execute(
                """
            SELECT count(*) AS count
            FROM msi_v2.outbox_jobs
            WHERE topic = 'finance.process_billing_enforcement_stage'
              AND payload->>'schedule_id' = %s
              AND payload->>'stage' = 'initial'
              AND available_at <= now() + INTERVAL '10 seconds'
            """,
                (str(live["schedule_id"]),),
            ).fetchone()["count"]
            == 1
        )
        assert repeated.version == profile.version
        assert (
            connection.execute(
                """
            SELECT count(*) AS count
            FROM msi_v2.invoices
            WHERE student_id = %s AND status <> 'voided'
            """,
                (int(enrollment["student_id"]),),
            ).fetchone()["count"]
            == 1
        )

        changed = configure_billing_profile(
            connection,
            command.model_copy(
                update={
                    "total_amount_minor": 2_200_000_00,
                    "expected_version": repeated.version,
                }
            ),
            actor=BillingActor(staff_id=None, account_id=None),
            scope=BillingSchoolScope(all_schools=True),
        )
        replacement = connection.execute(
            """
            SELECT cycle.id AS cycle_id, cycle.revision, cycle.due_at,
                   invoice.id AS invoice_id, invoice.total_minor,
                   schedule.deadline_at
            FROM msi_v2.student_billing_cycles cycle
            JOIN msi_v2.invoices invoice ON invoice.billing_cycle_id = cycle.id
            JOIN msi_v2.invoice_enforcement_schedules schedule
              ON schedule.invoice_id = invoice.id
            WHERE cycle.student_id = %s
              AND cycle.state = 'invoiced'
              AND invoice.status <> 'voided'
            """,
            (int(enrollment["student_id"]),),
        ).fetchone()
        assert replacement["revision"] == 2
        assert replacement["total_minor"] == 2_200_000_00
        assert replacement["due_at"] == replacement["deadline_at"]
        assert (
            connection.execute(
                """
            SELECT count(*) AS count
            FROM msi_v2.student_billing_cycles
            WHERE student_id = %s AND state = 'superseded'
            """,
                (int(enrollment["student_id"]),),
            ).fetchone()["count"]
            == 1
        )
        assert (
            connection.execute(
                "SELECT status FROM msi_v2.invoices WHERE id = %s",
                (int(live["invoice_id"]),),
            ).fetchone()["status"]
            == "voided"
        )

        next_cycle = configure_billing_profile(
            connection,
            command.model_copy(
                update={
                    "total_amount_minor": 2_400_000_00,
                    "expected_version": changed.version,
                    "apply_to": BillingScheduleApplyTo.NEXT_CYCLE,
                }
            ),
            actor=BillingActor(staff_id=None, account_id=None),
            scope=BillingSchoolScope(all_schools=True),
        )
        assert next_cycle.total_amount_minor == 2_400_000_00
        assert (
            connection.execute(
                """
            SELECT total_minor
            FROM msi_v2.invoices
            WHERE id = %s AND status <> 'voided'
            """,
                (int(replacement["invoice_id"]),),
            ).fetchone()["total_minor"]
            == 2_200_000_00
        )
        assert (
            connection.execute(
                """
            SELECT count(*) AS count
            FROM msi_v2.student_billing_cycles
            WHERE student_id = %s
            """,
                (int(enrollment["student_id"]),),
            ).fetchone()["count"]
            == 2
        )
    finally:
        connection.rollback()
        connection.close()


@pytest.mark.postgres
def test_identical_schedule_save_repairs_a_planned_cycle_without_an_invoice():
    connection = _connect_test_database()
    try:
        enrollment = _active_student_enrollment(connection)
        now = datetime.now(UTC)
        profile_id = billing_profile_repository.upsert_billing_profile(
            connection,
            student_id=int(enrollment["student_id"]),
            school_id=int(enrollment["school_id"]),
            billing_parent_id=None,
            billing_day=1,
            starts_on=now.date(),
            status=BillingProfileStatus.ACTIVE,
            pricing_mode=BillingPricingMode.TOTAL.value,
            total_amount_minor=2_000_000_00,
            expected_version=None,
            staff_id=None,
        )
        planned_cycle_ids = plan_billing_cycles(connection, now=now)
        assert planned_cycle_ids
        assert (
            connection.execute(
                """
            SELECT count(*) AS count
            FROM msi_v2.invoices
            WHERE student_id = %s AND status <> 'voided'
            """,
                (int(enrollment["student_id"]),),
            ).fetchone()["count"]
            == 0
        )

        command = ConfigureBillingProfileCommand(
            student_id=int(enrollment["student_id"]),
            billing_day=1,
            pricing_mode=BillingPricingMode.TOTAL,
            total_amount_minor=2_000_000_00,
            apply_to=BillingScheduleApplyTo.CURRENT_CYCLE,
            expected_version=1,
        )
        profile = configure_billing_profile(
            connection,
            command,
            actor=BillingActor(staff_id=None, account_id=None),
            scope=BillingSchoolScope(all_schools=True),
        )
        repeated = configure_billing_profile(
            connection,
            command,
            actor=BillingActor(staff_id=None, account_id=None),
            scope=BillingSchoolScope(all_schools=True),
        )

        live = connection.execute(
            """
            SELECT invoice.id, invoice.status,
                   schedule.countdown_started_at, schedule.deadline_at
            FROM msi_v2.invoices invoice
            JOIN msi_v2.invoice_enforcement_schedules schedule
              ON schedule.invoice_id = invoice.id
            WHERE invoice.student_id = %s AND invoice.status <> 'voided'
            """,
            (int(enrollment["student_id"]),),
        ).fetchone()
        assert live is not None
        assert live["status"] == "issued"
        assert live["deadline_at"] - live["countdown_started_at"] == timedelta(hours=48)
        assert profile.profile_id == profile_id
        assert repeated.version == profile.version
        assert (
            connection.execute(
                """
            SELECT count(*) AS count
            FROM msi_v2.invoices
            WHERE student_id = %s AND status <> 'voided'
            """,
                (int(enrollment["student_id"]),),
            ).fetchone()["count"]
            == 1
        )
    finally:
        connection.rollback()
        connection.close()


@pytest.mark.postgres
def test_empty_school_scope_automation_status_query_is_typed():
    connection = _connect_test_database()
    try:
        result = get_billing_automation_status(
            connection,
            scope=BillingSchoolScope(all_schools=True),
            now=datetime(2026, 7, 30, 8, tzinfo=UTC),
        )
        assert result.active_billing_profiles == 0
        assert result.open_invoices == 0
        assert result.worker_state.value == "not_started"
        assert result.last_successful_finance_worker_at is None
    finally:
        connection.rollback()
        connection.close()


@pytest.mark.postgres
def test_billing_accounts_include_missing_and_configured_schedules_without_invoices():
    connection = _connect_test_database()
    try:
        enrollment = _active_student_enrollment(connection)
        suffix = uuid4().hex[:10]
        student = connection.execute(
            """
            INSERT INTO msi_v2.students (student_code, full_name, school_id)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (
                f"BAC-{suffix}",
                f"Billing Account {suffix}",
                int(enrollment["school_id"]),
            ),
        ).fetchone()
        connection.execute(
            """
            INSERT INTO msi_v2.group_students (group_id, student_id)
            VALUES (%s, %s)
            """,
            (int(enrollment["group_id"]), int(student["id"])),
        )

        missing_page = list_billing_accounts(
            connection,
            scope=BillingSchoolScope(all_schools=True),
            query=f"BAC-{suffix}",
        )
        assert missing_page.total == 1
        assert missing_page.items[0].schedule_status.value == "missing"
        assert missing_page.items[0].latest_invoice is None

        profile_id = billing_profile_repository.upsert_billing_profile(
            connection,
            student_id=int(student["id"]),
            school_id=int(enrollment["school_id"]),
            billing_parent_id=None,
            billing_day=12,
            starts_on=date.today(),
            status=BillingProfileStatus.ACTIVE,
            expected_version=None,
            staff_id=None,
        )
        billing_profile_repository.replace_billing_items(
            connection,
            profile_id=profile_id,
            starts_on=date.today(),
            items=[
                (
                    int(enrollment["group_id"]),
                    int(enrollment["subject_id"]),
                    "Configured without an invoice",
                    275_000_00,
                )
            ],
            staff_id=None,
        )

        configured = get_billing_account(
            connection,
            scope=BillingSchoolScope(all_schools=True),
            account_type=BillingAccountType.STUDENT,
            account_id=int(student["id"]),
        )
        assert configured.schedule_status.value == "active"
        assert configured.billing_day == 12
        assert configured.monthly_amount_minor == 275_000_00
        assert configured.latest_invoice is None
        assert configured.schedule_items[0].group_id == int(enrollment["group_id"])
        assert configured.enrollment_options[0].subject_id == int(enrollment["subject_id"])
    finally:
        connection.rollback()
        connection.close()


@pytest.mark.postgres
def test_pending_admission_is_not_duplicated_after_activation():
    connection = _connect_test_database()
    try:
        enrollment = _active_student_enrollment(connection)
        suffix = uuid4().hex[:10]
        admission = connection.execute(
            """
            INSERT INTO msi_v2.admissions (
                school_id, student_full_name, parent_full_name, parent_phone,
                first_due_date, billing_day, status
            )
            VALUES (%s, %s, %s, %s, %s, 15, 'awaiting_payment')
            RETURNING id
            """,
            (
                int(enrollment["school_id"]),
                f"Pending Admission {suffix}",
                "Pending Parent",
                "+998900000000",
                date.today(),
            ),
        ).fetchone()
        connection.execute(
            """
            INSERT INTO msi_v2.admission_group_selections (
                admission_id, group_id, subject_id, monthly_amount_minor
            )
            VALUES (%s, %s, %s, %s)
            """,
            (
                int(admission["id"]),
                int(enrollment["group_id"]),
                int(enrollment["subject_id"]),
                300_000_00,
            ),
        )

        pending = list_billing_accounts(
            connection,
            scope=BillingSchoolScope(all_schools=True),
            query=f"Pending Admission {suffix}",
        )
        assert pending.total == 1
        assert pending.items[0].account_type.value == "admission"
        assert pending.items[0].monthly_amount_minor == 300_000_00

        connection.execute(
            """
            UPDATE msi_v2.admissions
            SET activated_student_id = %s, status = 'active'
            WHERE id = %s
            """,
            (int(enrollment["student_id"]), int(admission["id"])),
        )
        activated = list_billing_accounts(
            connection,
            scope=BillingSchoolScope(all_schools=True),
            query=f"Pending Admission {suffix}",
        )
        assert activated.total == 0
    finally:
        connection.rollback()
        connection.close()
