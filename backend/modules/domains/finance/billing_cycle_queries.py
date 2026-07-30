"""Typed read models for billing-cycle readiness and parent schedules."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from backend.core.clock import SystemClock
from backend.core.unit_of_work import Connection
from backend.modules.domains.finance import billing_cycle_repository as repository
from backend.modules.domains.finance import enforcement_repository
from backend.modules.domains.finance.domain_types import (
    BillingCycleReviewDecision,
    BillingCycleReviewStatus,
    BillingCycleState,
    InvoiceOrigin,
    InvoiceStatus,
)
from backend.modules.domains.finance.policies import PAYMENT_WINDOW_HOURS
from backend.modules.domains.finance.schemas import (
    BillingCycleInvoiceCandidate,
    BillingCycleItemResult,
    BillingCycleReadiness,
    BillingCycleReviewResult,
    BillingCycleSummary,
)


class BillingReadScope(Protocol):
    @property
    def school_ids(self) -> frozenset[int]: ...

    @property
    def all_schools(self) -> bool: ...


def _candidate(row: Any) -> BillingCycleInvoiceCandidate:
    return BillingCycleInvoiceCandidate(
        invoice_id=int(row["id"]),
        invoice_number=str(row["invoice_number"]),
        total_minor=int(row["total_minor"]),
        completed_minor=int(row["paid_minor"]),
        available_minor=int(row["available_minor"]),
        currency=str(row["currency"]),
        origin=InvoiceOrigin(str(row["origin"])),
        status=InvoiceStatus(str(row["status"])),
        paid_at=row["paid_at"],
    )


def _review(row: Any) -> BillingCycleReviewResult:
    return BillingCycleReviewResult(
        review_id=int(row["id"]),
        cycle_id=int(row["cycle_id"]),
        invoice_id=int(row["invoice_id"]),
        invoice_number=str(row["invoice_number"]),
        decision=BillingCycleReviewDecision(str(row["decision"])),
        allocated_minor=int(row["allocated_minor"]),
        status=BillingCycleReviewStatus(str(row["status"])),
        reason=str(row["reason"]),
        reviewed_at=row["reviewed_at"],
        reversed_at=row["reversed_at"],
        reversal_reason=str(row["reversal_reason"]),
        version=int(row["version"]),
    )


def cycle_summary(conn: Connection, row: Any) -> BillingCycleSummary:
    cycle_id = int(row["id"])
    due_at = row["due_at"]
    remaining_minor = (
        max(0, int(row["invoice_total_minor"]) - int(row["invoice_paid_minor"]))
        if row.get("invoice_id") is not None
        else int(row["expected_minor"]) - int(row["allocated_minor"])
    )
    return BillingCycleSummary(
        cycle_id=cycle_id,
        profile_id=int(row["profile_id"]),
        student_id=int(row["student_id"]),
        student_row_id=(
            int(row["legacy_student_row_id"])
            if row["legacy_student_row_id"] is not None
            else None
        ),
        student_name=str(row["student_name"]),
        student_code=str(row["student_code"]),
        school_id=int(row["school_id"]),
        school_name=str(row["school_name"]),
        billing_period=row["billing_period"],
        deadline_at=row.get("effective_deadline_at") or due_at,
        issue_at=due_at - timedelta(hours=PAYMENT_WINDOW_HOURS),
        currency=str(row["currency"]),
        expected_minor=int(row["expected_minor"]),
        allocated_minor=int(row["allocated_minor"]),
        remaining_minor=remaining_minor,
        state=BillingCycleState(str(row["state"])),
        invoice_id=(int(row["invoice_id"]) if row["invoice_id"] is not None else None),
        invoice_number=str(row["invoice_number"] or ""),
        version=int(row["version"]),
        items=[
            BillingCycleItemResult(
                cycle_item_id=int(item["id"]),
                group_id=(int(item["group_id"]) if item["group_id"] is not None else None),
                subject_id=(
                    int(item["subject_id"]) if item["subject_id"] is not None else None
                ),
                description=str(item["description"]),
                amount_minor=int(item["amount_minor"]),
            )
            for item in repository.list_cycle_item_rows(conn, cycle_id)
        ],
        reviews=[_review(item) for item in repository.list_cycle_review_rows(conn, cycle_id)],
        review_candidates=[
            _candidate(item) for item in repository.list_manual_candidate_rows(conn, cycle_id)
        ],
    )


def _recipient_summary(conn: Connection, cycles: list[BillingCycleSummary]) -> tuple[int, int]:
    student_ids = {
        cycle.student_id
        for cycle in cycles
        if cycle.state not in {BillingCycleState.SATISFIED, BillingCycleState.CANCELLED}
    }
    recipients: dict[str, Any] = {}
    for student_id in student_ids:
        for target in enforcement_repository.list_household_target_rows(conn, student_id):
            key = (
                f"telegram:{target['telegram_user_id']}"
                if target["telegram_user_id"] is not None
                else f"{target['target_type']}:{target['person_id']}"
            )
            recipients[key] = target
    linked = sum(target["telegram_user_id"] is not None for target in recipients.values())
    return linked, len(recipients) - linked


def get_billing_cycle_readiness(
    conn: Connection,
    *,
    scope: BillingReadScope,
    now: datetime | None = None,
) -> BillingCycleReadiness:
    generated_at = (now or SystemClock().now()).astimezone(UTC)
    cycles = [
        cycle_summary(conn, row)
        for row in repository.list_scoped_cycle_rows(
            conn,
            school_ids=scope.school_ids,
            all_schools=scope.all_schools,
            limit=500,
        )
    ]
    linked_recipients, unlinked_recipients = _recipient_summary(conn, cycles)
    return BillingCycleReadiness(
        generated_at=generated_at,
        effective_school_ids=list(scope.school_ids),
        scheduled_cycles=sum(cycle.state is BillingCycleState.SCHEDULED for cycle in cycles),
        review_required_cycles=sum(
            cycle.state is BillingCycleState.REVIEW_REQUIRED for cycle in cycles
        ),
        ready_to_issue_cycles=sum(
            cycle.state is BillingCycleState.SCHEDULED
            and cycle.issue_at <= generated_at
            and cycle.remaining_minor > 0
            for cycle in cycles
        ),
        satisfied_cycles=sum(cycle.state is BillingCycleState.SATISFIED for cycle in cycles),
        potential_hold_count=sum(
            cycle.state in {BillingCycleState.SCHEDULED, BillingCycleState.INVOICED}
            and cycle.remaining_minor > 0
            for cycle in cycles
        ),
        linked_telegram_recipients=linked_recipients,
        unlinked_telegram_recipients=unlinked_recipients,
        cycles=cycles,
    )


__all__ = ["cycle_summary", "get_billing_cycle_readiness"]
