"""Monthly billing-cycle planning, review, and issuance use cases."""

from __future__ import annotations

from calendar import monthrange
from datetime import UTC, date, datetime, time, timedelta
from typing import Protocol

from backend.core.clock import SystemClock
from backend.core.time import SCHOOL_TIMEZONE
from backend.core.unit_of_work import Connection
from backend.modules.domains.finance import billing_cycle_repository as repository
from backend.modules.domains.finance import enforcement, ledger_repository
from backend.modules.domains.finance.billing_cycle_queries import cycle_summary
from backend.modules.domains.finance.domain_types import (
    BillingCycleReviewDecision,
    BillingCycleReviewStatus,
    BillingCycleState,
    BillingJobTopic,
)
from backend.modules.domains.finance.policies import PAYMENT_WINDOW_HOURS, BillingError
from backend.modules.domains.finance.schemas import (
    BillingCycleSummary,
    ReverseBillingCycleReviewCommand,
    ReviewBillingCycleInvoiceCommand,
)
from backend.modules.jobs.contracts import enqueue_on_connection
from backend.modules.jobs.schemas import EnqueueJobCommand

BILLING_DEADLINE_TIME = time(hour=0, minute=5)


class BillingScope(Protocol):
    @property
    def school_ids(self) -> frozenset[int]: ...

    @property
    def all_schools(self) -> bool: ...

    def allows(self, school_id: int) -> bool: ...


class BillingAuditActor(Protocol):
    @property
    def staff_id(self) -> int | None: ...

    @property
    def account_id(self) -> int | None: ...


def _next_month(period: date) -> date:
    if period.month == 12:
        return date(period.year + 1, 1, 1)
    return date(period.year, period.month + 1, 1)


def _month_start(value: date) -> date:
    return value.replace(day=1)


def cycle_deadline(period: date, billing_day: int) -> datetime:
    day = min(max(int(billing_day), 1), monthrange(period.year, period.month)[1], 28)
    return datetime.combine(
        period.replace(day=day),
        BILLING_DEADLINE_TIME,
        tzinfo=SCHOOL_TIMEZONE,
    ).astimezone(UTC)


def next_billing_period(
    *,
    now: datetime,
    billing_day: int,
    starts_on: date,
) -> date:
    school_now = now.astimezone(SCHOOL_TIMEZONE)
    period = _month_start(max(school_now.date(), starts_on))
    deadline = cycle_deadline(period, billing_day)
    if deadline <= now.astimezone(UTC):
        period = _next_month(period)
    while period < _month_start(starts_on):
        period = _next_month(period)
    return period


def _enqueue_cycle_issuance(
    conn: Connection,
    *,
    cycle_id: int,
    cycle_version: int,
    issue_at: datetime,
    now: datetime,
) -> None:
    enqueue_on_connection(
        conn,
        EnqueueJobCommand(
            topic=BillingJobTopic.ISSUE_BILLING_CYCLE.value,
            payload={"cycle_id": cycle_id},
            idempotency_key=f"finance-issue-billing-cycle:{cycle_id}:v{cycle_version}",
            available_at=max(issue_at, now.astimezone(UTC)),
            max_attempts=10,
        ),
    )


def plan_billing_cycles(conn: Connection, *, now: datetime) -> list[int]:
    planned_cycle_ids: list[int] = []
    normalized_now = now.astimezone(UTC)
    for profile in repository.list_active_profile_rows(conn):
        period = next_billing_period(
            now=normalized_now,
            billing_day=int(profile["billing_day"]),
            starts_on=profile["starts_on"],
        )
        if profile["ends_on"] is not None and period > _month_start(profile["ends_on"]):
            continue
        deadline = cycle_deadline(period, int(profile["billing_day"]))
        items = repository.list_snapshot_item_rows(
            conn,
            profile_id=int(profile["id"]),
            effective_on=deadline.astimezone(SCHOOL_TIMEZONE).date(),
        )
        cycle_id = repository.insert_cycle(
            conn,
            profile_id=int(profile["id"]),
            student_id=int(profile["student_id"]),
            school_id=int(profile["school_id"]),
            billing_period=period,
            due_at=deadline,
            item_rows=items,
        )
        if not cycle_id:
            continue
        cycle = repository.get_cycle_row(conn, cycle_id)
        if not cycle or str(cycle["state"]) in {
            BillingCycleState.SATISFIED.value,
            BillingCycleState.CANCELLED.value,
            BillingCycleState.INVOICED.value,
        }:
            continue
        if repository.list_manual_candidate_rows(conn, cycle_id):
            repository.update_cycle_state(
                conn,
                cycle_id=cycle_id,
                state=BillingCycleState.REVIEW_REQUIRED.value,
            )
            cycle = repository.get_cycle_row(conn, cycle_id)
        _enqueue_cycle_issuance(
            conn,
            cycle_id=cycle_id,
            cycle_version=int(cycle["version"]),
            issue_at=deadline - timedelta(hours=PAYMENT_WINDOW_HOURS),
            now=normalized_now,
        )
        planned_cycle_ids.append(cycle_id)
    return planned_cycle_ids


def issue_billing_cycle(
    conn: Connection,
    *,
    cycle_id: int,
    now: datetime,
) -> int:
    cycle = repository.get_cycle_row(conn, cycle_id, for_update=True)
    if not cycle:
        return 0
    if str(cycle["state"]) in {
        BillingCycleState.CANCELLED.value,
        BillingCycleState.SATISFIED.value,
    }:
        return 0
    if cycle["invoice_id"] is not None:
        repository.update_cycle_state(
            conn,
            cycle_id=cycle_id,
            state=BillingCycleState.INVOICED.value,
        )
        return int(cycle["invoice_id"])
    if repository.list_manual_candidate_rows(conn, cycle_id):
        repository.update_cycle_state(
            conn,
            cycle_id=cycle_id,
            state=BillingCycleState.REVIEW_REQUIRED.value,
        )
        return 0
    cycle = repository.recompute_cycle_allocation(conn, cycle_id)
    remaining_minor = int(cycle["expected_minor"]) - int(cycle["allocated_minor"])
    if remaining_minor <= 0:
        repository.update_cycle_state(
            conn,
            cycle_id=cycle_id,
            state=BillingCycleState.SATISFIED.value,
        )
        return 0
    normalized_now = now.astimezone(UTC)
    planned_issue_at = cycle["due_at"] - timedelta(hours=PAYMENT_WINDOW_HOURS)
    deadline_at = (
        normalized_now + timedelta(hours=PAYMENT_WINDOW_HOURS)
        if normalized_now > planned_issue_at
        else cycle["due_at"]
    )
    parent_id = ledger_repository.find_billing_parent_id(
        conn,
        int(cycle["student_id"]),
    )
    invoice_id = repository.insert_cycle_invoice(
        conn,
        cycle_row=cycle,
        item_rows=repository.list_cycle_item_rows(conn, cycle_id),
        remaining_minor=remaining_minor,
        due_date=deadline_at.astimezone(SCHOOL_TIMEZONE).date(),
        parent_id=parent_id,
        invoice_number=ledger_repository.next_invoice_number(conn),
    )
    if not invoice_id:
        return 0
    repository.update_cycle_state(
        conn,
        cycle_id=cycle_id,
        state=BillingCycleState.INVOICED.value,
    )
    enforcement.start_invoice_enforcement(
        conn,
        invoice_id=invoice_id,
        now=normalized_now,
        countdown_started_at=deadline_at - timedelta(hours=PAYMENT_WINDOW_HOURS),
        deadline_at=deadline_at,
    )
    ledger_repository.insert_audit_event(
        conn,
        event_type="finance.billing_cycle_invoiced",
        entity_type="billing_cycle",
        entity_id=cycle_id,
        detail={
            "invoice_id": invoice_id,
            "expected_minor": int(cycle["expected_minor"]),
            "allocated_minor": int(cycle["allocated_minor"]),
            "invoice_minor": remaining_minor,
            "deadline_at": deadline_at.isoformat(),
        },
        staff_id=None,
        account_id=None,
    )
    return invoice_id


def review_manual_invoice(
    conn: Connection,
    command: ReviewBillingCycleInvoiceCommand,
    *,
    actor: BillingAuditActor,
    scope: BillingScope,
) -> BillingCycleSummary:
    cycle = repository.get_cycle_row(conn, command.cycle_id, for_update=True)
    if not cycle or not scope.allows(int(cycle["school_id"])):
        raise BillingError(
            "Billing cycle was not found.",
            code="billing_cycle_not_found",
            status_code=404,
        )
    if int(cycle["version"]) != command.expected_cycle_version:
        raise BillingError(
            "The billing cycle changed. Reload and try again.",
            code="billing_cycle_version_conflict",
            status_code=409,
        )
    if cycle["invoice_id"] is not None:
        raise BillingError(
            "The billing cycle already has an invoice.",
            code="billing_cycle_already_invoiced",
            status_code=409,
        )
    ledger_repository.get_invoice_row(
        conn,
        invoice_id=command.invoice_id,
        for_update=True,
    )
    candidate = repository.get_available_manual_invoice_row(
        conn,
        cycle_id=command.cycle_id,
        invoice_id=command.invoice_id,
        require_matching_period=command.decision is BillingCycleReviewDecision.EXCLUDE,
    )
    if candidate is None:
        raise BillingError(
            "The manual invoice is not available for this billing cycle.",
            code="billing_invoice_not_available",
            status_code=409,
        )
    cycle_remaining = int(cycle["expected_minor"]) - int(cycle["allocated_minor"])
    if command.allocated_minor > min(int(candidate["available_minor"]), cycle_remaining):
        raise BillingError(
            "The allocation exceeds the invoice payment or cycle balance.",
            code="billing_allocation_exceeds_balance",
            status_code=409,
        )
    review_id = repository.insert_review(
        conn,
        cycle_id=command.cycle_id,
        invoice_id=command.invoice_id,
        decision=command.decision.value,
        allocated_minor=command.allocated_minor,
        reason=command.reason,
        staff_id=actor.staff_id,
    )
    cycle = repository.recompute_cycle_allocation(conn, command.cycle_id)
    candidates = repository.list_manual_candidate_rows(conn, command.cycle_id)
    if int(cycle["allocated_minor"]) >= int(cycle["expected_minor"]):
        state = BillingCycleState.SATISFIED
    elif candidates:
        state = BillingCycleState.REVIEW_REQUIRED
    else:
        state = BillingCycleState.SCHEDULED
    repository.update_cycle_state(
        conn,
        cycle_id=command.cycle_id,
        state=state.value,
    )
    refreshed = repository.get_cycle_row(conn, command.cycle_id)
    if state is BillingCycleState.SCHEDULED:
        _enqueue_cycle_issuance(
            conn,
            cycle_id=command.cycle_id,
            cycle_version=int(refreshed["version"]),
            issue_at=refreshed["due_at"] - timedelta(hours=PAYMENT_WINDOW_HOURS),
            now=SystemClock().now(),
        )
    ledger_repository.insert_audit_event(
        conn,
        event_type="finance.billing_cycle_invoice_reviewed",
        entity_type="billing_cycle_invoice_review",
        entity_id=review_id,
        detail={
            "cycle_id": command.cycle_id,
            "invoice_id": command.invoice_id,
            "decision": command.decision.value,
            "allocated_minor": command.allocated_minor,
            "reason": command.reason,
        },
        staff_id=actor.staff_id,
        account_id=actor.account_id,
    )
    return cycle_summary(conn, repository.get_cycle_row(conn, command.cycle_id))


def reverse_manual_invoice_review(
    conn: Connection,
    review_id: int,
    command: ReverseBillingCycleReviewCommand,
    *,
    actor: BillingAuditActor,
    scope: BillingScope,
) -> BillingCycleSummary:
    review = repository.get_review_row(conn, review_id, for_update=True)
    if not review or not scope.allows(int(review["school_id"])):
        raise BillingError(
            "Billing review was not found.",
            code="billing_review_not_found",
            status_code=404,
        )
    if str(review["status"]) != BillingCycleReviewStatus.ACTIVE.value:
        raise BillingError("The billing review is already reversed.", status_code=409)
    cycle = repository.get_cycle_row(conn, int(review["cycle_id"]), for_update=True)
    if cycle["invoice_id"] is not None:
        raise BillingError(
            "Void the generated cycle invoice before reversing this allocation.",
            code="billing_cycle_invoice_exists",
            status_code=409,
        )
    if not repository.reverse_review(
        conn,
        review_id=review_id,
        expected_version=command.expected_version,
        staff_id=actor.staff_id,
        reason=command.reason,
    ):
        raise BillingError(
            "The billing review changed. Reload and try again.",
            code="billing_review_version_conflict",
            status_code=409,
        )
    repository.recompute_cycle_allocation(conn, int(review["cycle_id"]))
    repository.update_cycle_state(
        conn,
        cycle_id=int(review["cycle_id"]),
        state=BillingCycleState.REVIEW_REQUIRED.value,
    )
    ledger_repository.insert_audit_event(
        conn,
        event_type="finance.billing_cycle_review_reversed",
        entity_type="billing_cycle_invoice_review",
        entity_id=review_id,
        detail={"reason": command.reason},
        staff_id=actor.staff_id,
        account_id=actor.account_id,
    )
    return cycle_summary(conn, repository.get_cycle_row(conn, int(review["cycle_id"])))


__all__ = [
    "BILLING_DEADLINE_TIME",
    "cycle_deadline",
    "issue_billing_cycle",
    "next_billing_period",
    "plan_billing_cycles",
    "review_manual_invoice",
    "reverse_manual_invoice_review",
]
