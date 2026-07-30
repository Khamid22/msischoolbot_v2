from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from backend.application.security_middleware import _payment_only_path_allowed
from backend.modules.domains.finance import enforcement
from backend.modules.domains.finance.domain_types import (
    BillingAccessMode,
    BillingHoldTarget,
    BillingNotificationStage,
)
from backend.modules.domains.finance.module import MODULE
from backend.modules.domains.finance.notification_sender import (
    billing_notification_text,
)
from backend.modules.domains.finance.policies import (
    PAYMENT_WINDOW_HOURS,
    enforcement_deadline,
    enforcement_start,
)
from tests.test_route_snapshot import flatten_routes


def test_invoice_always_gets_a_complete_48_hour_window():
    issued_at = datetime(2026, 7, 28, 8, tzinfo=UTC)
    deadline = enforcement_deadline(
        issued_at=issued_at,
        due_date=date(2026, 7, 1),
    )

    assert deadline == issued_at + timedelta(hours=PAYMENT_WINDOW_HOURS)
    assert enforcement_start(deadline) == issued_at


def test_future_due_date_starts_countdown_exactly_48_hours_before_deadline():
    deadline = enforcement_deadline(
        issued_at=datetime(2026, 7, 1, 8, tzinfo=UTC),
        due_date=date(2026, 8, 1),
    )

    assert deadline - enforcement_start(deadline) == timedelta(hours=48)


def test_sibling_notification_does_not_reveal_invoice_details():
    message = billing_notification_text(
        stage=BillingNotificationStage.TWENTY_FOUR_HOURS,
        target_type=BillingHoldTarget.HOUSEHOLD_STUDENT,
        language="uz",
        student_name="Other child",
        invoice_number="INV-PRIVATE",
        balance_minor=10_000_000,
        currency="UZS",
        deadline_at=datetime(2026, 7, 30, 8, tzinfo=UTC),
    )

    assert "INV-PRIVATE" not in message
    assert "Other child" not in message
    assert "10 000 000" not in message
    assert "24 soat" in message


def test_account_access_hides_sibling_invoice_details(monkeypatch):
    now = datetime(2026, 7, 28, 8, tzinfo=UTC)
    deadline = now + timedelta(hours=6)
    rows = [
        {
            "invoice_id": 10,
            "invoice_number": "INV-10",
            "student_id": 100,
            "legacy_student_row_id": 1_000,
            "student_name": "Own child",
            "student_code": "ST100",
            "total_minor": 2_000_000,
            "paid_minor": 0,
            "currency": "UZS",
            "deadline_at": deadline,
            "target_type": BillingHoldTarget.LINKED_PARENT.value,
            "hold_status": "active",
        },
        {
            "invoice_id": 11,
            "invoice_number": "INV-11",
            "student_id": 101,
            "legacy_student_row_id": 1_001,
            "student_name": "Sibling account",
            "student_code": "ST101",
            "total_minor": 3_000_000,
            "paid_minor": 0,
            "currency": "UZS",
            "deadline_at": deadline,
            "target_type": BillingHoldTarget.HOUSEHOLD_STUDENT.value,
            "hold_status": "active",
        },
    ]
    monkeypatch.setattr(
        enforcement.repository,
        "list_account_enforcement_rows",
        lambda _conn, _account_id: rows,
    )

    status = enforcement.account_billing_access(
        object(),
        account_id=25,
        now=now,
    )

    assert status.mode is BillingAccessMode.PAYMENT_ONLY
    assert status.blocking_invoice_count == 2
    assert [invoice.invoice_number for invoice in status.invoices] == ["INV-10"]
    assert len(status.affected_students) == 2


def test_payment_only_allowlist_keeps_only_payment_support_and_logout_routes():
    assert _payment_only_path_allowed("/parent/payments")
    assert _payment_only_path_allowed("/api/v1/parent/billing-status")
    assert _payment_only_path_allowed("/api/v1/student/support/tickets")
    assert _payment_only_path_allowed("/logout")
    assert not _payment_only_path_allowed("/parent/children")
    assert not _payment_only_path_allowed("/api/v1/student/chat/messages")


def test_migration_is_additive_and_bootstraps_existing_open_invoices():
    source = (
        Path(__file__).parents[1]
        / "database/alembic/versions/0048_billing_enforcement.py"
    ).read_text(encoding="utf-8")
    upgrade_source = source.split("def downgrade", 1)[0].upper()

    assert "INVOICE_ENFORCEMENT_SCHEDULES" in upgrade_source
    assert "BILLING_ACCESS_HOLDS" in upgrade_source
    assert "BILLING_NOTIFICATION_DELIVERIES" in upgrade_source
    assert "FINANCE.BOOTSTRAP_BILLING_ENFORCEMENT" in upgrade_source
    assert "DELETE FROM" not in upgrade_source
    assert " TRUNCATE " not in upgrade_source
    assert " DROP TABLE " not in upgrade_source


def test_finance_module_registers_generation_reminder_delivery_and_reconciliation():
    topics = {handler.topic for handler in MODULE.job_handlers}

    assert topics == {
        "finance.generate_invoices",
        "finance.issue_billing_cycle",
        "finance.bootstrap_billing_enforcement",
        "finance.process_billing_enforcement_stage",
        "finance.send_billing_notification",
        "finance.reconcile_billing_enforcement",
    }


def test_parent_and_student_payment_only_routes_are_registered(app):
    paths = {entry.split(" | ", 1)[0] for entry in flatten_routes(app)}

    assert "/api/v1/parent/billing-status" in paths
    assert "/api/v1/student/billing-status" in paths
    assert "/api/v1/student/payments" in paths
    assert "/api/v1/student/support/tickets" in paths
    assert "/student/payments" in paths
    assert "/student/support" in paths
