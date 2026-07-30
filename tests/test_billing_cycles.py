"""Billing-cycle timing, review, and delivery-contract regressions."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

from backend.core.time import SCHOOL_TIMEZONE
from backend.modules.domains.finance.billing_cycles import (
    cycle_deadline,
    next_billing_period,
)
from backend.modules.domains.finance.domain_types import BillingCycleReviewDecision
from backend.modules.domains.finance.schemas import ReviewBillingCycleInvoiceCommand


@pytest.mark.parametrize(
    ("period", "billing_day", "expected_local"),
    [
        (date(2026, 8, 1), 1, datetime(2026, 8, 1, 0, 5, tzinfo=SCHOOL_TIMEZONE)),
        (date(2026, 12, 1), 28, datetime(2026, 12, 28, 0, 5, tzinfo=SCHOOL_TIMEZONE)),
        (date(2027, 1, 1), 1, datetime(2027, 1, 1, 0, 5, tzinfo=SCHOOL_TIMEZONE)),
    ],
)
def test_cycle_deadline_is_0005_school_time(
    period: date,
    billing_day: int,
    expected_local: datetime,
):
    assert cycle_deadline(period, billing_day) == expected_local.astimezone(UTC)


def test_invoice_issue_time_is_exactly_48_hours_before_cycle_deadline():
    deadline = cycle_deadline(date(2026, 8, 1), 1)

    assert deadline - timedelta(hours=48) == datetime(2026, 7, 29, 19, 5, tzinfo=UTC)


def test_next_cycle_crosses_year_after_deadline():
    period = next_billing_period(
        now=datetime(2026, 12, 28, 0, 6, tzinfo=SCHOOL_TIMEZONE),
        billing_day=28,
        starts_on=date(2026, 1, 1),
    )

    assert period == date(2027, 1, 1)


def test_next_cycle_remains_current_month_before_deadline():
    period = next_billing_period(
        now=datetime(2026, 7, 30, 12, 0, tzinfo=SCHOOL_TIMEZONE),
        billing_day=1,
        starts_on=date(2026, 7, 29),
    )

    assert period == date(2026, 8, 1)


def test_apply_review_requires_a_positive_allocation():
    with pytest.raises(ValueError, match="positive"):
        ReviewBillingCycleInvoiceCommand(
            cycle_id=1,
            invoice_id=2,
            decision=BillingCycleReviewDecision.APPLY,
            allocated_minor=0,
            reason="Apply payment.",
            expected_cycle_version=1,
        )


def test_excluded_review_cannot_allocate_money():
    with pytest.raises(ValueError, match="cannot allocate"):
        ReviewBillingCycleInvoiceCommand(
            cycle_id=1,
            invoice_id=2,
            decision=BillingCycleReviewDecision.EXCLUDE,
            allocated_minor=100,
            reason="Different service.",
            expected_cycle_version=1,
        )


def test_billing_cycle_migration_is_additive_and_never_auto_allocates_legacy_money():
    source = Path(
        "database/alembic/versions/0050_student_billing_cycles.py"
    ).read_text(encoding="utf-8")
    upgrade = source.split("def downgrade()", 1)[0]

    assert "student_billing_cycles" in upgrade
    assert "student_billing_cycle_items" in upgrade
    assert "billing_cycle_invoice_reviews" in upgrade
    assert "billing_cycle_id" in upgrade
    assert "review_required" in upgrade
    assert "DELETE FROM" not in upgrade.upper()
    assert "TRUNCATE " not in upgrade.upper()
    assert "DROP TABLE " not in upgrade.upper()
    assert "INSERT INTO msi_v2.billing_cycle_invoice_reviews" not in upgrade


def test_customer_support_api_exposes_review_and_reversal_without_delete_routes():
    source = Path(
        "backend/modules/people/customer_support/workspace/payments_api.py"
    ).read_text(encoding="utf-8")

    assert '"/billing-cycles/readiness"' in source
    assert '"/billing-cycles/{cycle_id}/invoice-review"' in source
    assert '"/billing-cycle-reviews/{review_id}/reversal"' in source
    assert "@router.delete" not in source
