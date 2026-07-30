"""Regressions for non-destructive billing schedule replacement and observability."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from backend.modules.domains.finance import billing_profile_repository, queries
from backend.modules.domains.finance.domain_types import (
    BillingAutomationWorkerState,
    BillingEnforcementState,
    BillingNotificationDeliveryStatus,
    BillingNotificationStage,
)
from backend.modules.domains.finance.queries import BillingSchoolScope


class _Rows:
    def fetchall(self):
        return []


class _Connection:
    def __init__(self):
        self.calls: list[tuple[str, object]] = []

    def execute(self, sql, params=None):
        self.calls.append((sql, params))
        return _Rows()


def test_same_day_billing_replacement_cancels_before_upserting():
    conn = _Connection()

    billing_profile_repository.replace_billing_items(
        conn,  # type: ignore[arg-type]
        profile_id=17,
        starts_on=date(2026, 7, 30),
        items=[(21, 31, "Mathematics", 150_000_00)],
        staff_id=9,
    )

    cancellation_sql, cancellation_params = conn.calls[0]
    ending_sql, ending_params = conn.calls[1]
    upsert_sql, _upsert_params = conn.calls[2]
    assert "SET status = 'cancelled'" in cancellation_sql
    assert "active_from >= %s" in cancellation_sql
    assert cancellation_params == (9, 17, date(2026, 7, 30))
    assert "active_from < %s" in ending_sql
    assert "active_until = %s - 1" in ending_sql
    assert ending_params == (
        date(2026, 7, 30),
        17,
        date(2026, 7, 30),
        date(2026, 7, 30),
    )
    assert "status = 'active'" in upsert_sql
    assert "cancelled_at = NULL" in upsert_sql
    assert "DELETE " not in "\n".join(sql for sql, _params in conn.calls).upper()


def test_invoice_generation_reads_only_active_billing_items():
    source = Path("backend/modules/domains/finance/billing_profile_repository.py").read_text(
        encoding="utf-8"
    )

    assert "AND item.status = 'active'" in source


def test_billing_reliability_migration_is_additive():
    source = Path("database/alembic/versions/0049_billing_reliability.py").read_text(
        encoding="utf-8"
    )
    upgrade = source.split("def downgrade()", 1)[0]

    assert 'down_revision = "0048_billing_enforcement"' in source
    assert "DELETE FROM" not in upgrade.upper()
    assert "TRUNCATE " not in upgrade.upper()
    assert "ADD COLUMN IF NOT EXISTS status" in upgrade
    assert "status IN ('active', 'cancelled')" in upgrade
    assert "cancelled_by_staff_id" in upgrade


def test_notification_timeline_reports_delivery_results_without_recipients(monkeypatch):
    now = datetime(2026, 7, 30, 8, tzinfo=UTC)
    monkeypatch.setattr(
        queries.enforcement_repository,
        "get_schedule_by_invoice_row",
        lambda *_args, **_kwargs: {
            "id": 4,
            "state": "countdown",
            "countdown_started_at": now,
            "deadline_at": now + timedelta(hours=48),
            "cleared_at": None,
            "updated_at": now,
        },
    )
    monkeypatch.setattr(
        queries.enforcement_repository,
        "list_notification_delivery_summary_rows",
        lambda *_args, **_kwargs: [
            {
                "stage": "initial",
                "status": "sent",
                "delivery_count": 2,
                "first_created_at": now,
            },
            {
                "stage": "initial",
                "status": "skipped",
                "delivery_count": 1,
                "first_created_at": now,
            },
        ],
    )

    timeline = queries._notification_timeline(object(), invoice_id=81)  # type: ignore[arg-type]

    assert [entry.stage for entry in timeline] == [
        BillingNotificationStage.INITIAL,
        BillingNotificationStage.TWENTY_FOUR_HOURS,
        BillingNotificationStage.SIX_HOURS,
        BillingNotificationStage.HELD,
    ]
    assert timeline[0].status is BillingNotificationDeliveryStatus.SENT
    assert timeline[0].recipient_count == 3
    assert timeline[0].sent_count == 2
    assert timeline[0].skipped_count == 1


def test_notification_timeline_keeps_failed_delivery_visible():
    status = queries._timeline_status(
        counts={"pending": 2, "failed": 1},
        schedule_state=BillingEnforcementState.COUNTDOWN,
    )

    assert status is BillingNotificationDeliveryStatus.FAILED


def test_automation_status_marks_an_inactive_finance_worker_as_stalled(monkeypatch):
    now = datetime(2026, 7, 30, 8, tzinfo=UTC)
    monkeypatch.setattr(
        queries.automation_repository,
        "get_automation_status_row",
        lambda *_args, **_kwargs: {
            "active_billing_profiles": 12,
            "currently_due_billing_profiles": 8,
            "open_invoices": 5,
            "open_invoices_without_enforcement": 2,
            "linked_telegram_recipients": 9,
            "unlinked_telegram_recipients": 3,
            "pending_notification_deliveries": 4,
            "failed_notification_deliveries": 1,
            "active_payment_only_holds": 2,
            "pending_job_count": 7,
            "last_completed_at": now - timedelta(hours=2),
        },
    )

    result = queries.get_billing_automation_status(
        object(),  # type: ignore[arg-type]
        scope=BillingSchoolScope(school_ids=frozenset({5})),
        now=now,
    )

    assert result.worker_state is BillingAutomationWorkerState.STALLED
    assert result.effective_school_ids == [5]
    assert result.open_invoices_without_enforcement == 2
    assert result.unlinked_telegram_recipients == 3
