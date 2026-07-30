"""Monthly billing-cycle planning, review, and issuance use cases."""

from __future__ import annotations

from calendar import monthrange
from datetime import UTC, date, datetime, time, timedelta
from typing import Any, Protocol

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
    BillingPricingMode,
    BillingScheduleApplyTo,
    InvoiceStatus,
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


def _cycle_snapshot(
    conn: Connection,
    *,
    profile: Any,
    effective_on: date,
) -> tuple[list[dict[str, Any]], list[Any], list[int]]:
    student_id = int(profile["student_id"])
    coverage = repository.list_active_enrollment_rows(conn, student_id=student_id)
    if not coverage:
        return [], [], []
    pricing_mode = BillingPricingMode(str(profile["pricing_mode"]))
    if pricing_mode is BillingPricingMode.TOTAL:
        return (
            [
                {
                    "id": None,
                    "group_id": None,
                    "subject_id": None,
                    "description": "Monthly tuition",
                    "amount_minor": int(profile["total_amount_minor"]),
                }
            ],
            coverage,
            [],
        )
    prices = {
        int(row["subject_id"]): row
        for row in repository.list_subject_price_rows(
            conn,
            profile_id=int(profile["id"]),
            effective_on=effective_on,
        )
    }
    covered_subject_ids = {int(row["subject_id"]) for row in coverage}
    missing_subject_ids = sorted(covered_subject_ids - prices.keys())
    if missing_subject_ids:
        return [], coverage, missing_subject_ids
    items: list[dict[str, Any]] = [
        {
            "id": None,
            "group_id": None,
            "subject_id": subject_id,
            "description": str(prices[subject_id]["subject_name"]),
            "amount_minor": int(prices[subject_id]["amount_minor"]),
        }
        for subject_id in sorted(
            covered_subject_ids,
            key=lambda value: str(prices[value]["subject_name"]).casefold(),
        )
    ]
    return items, coverage, []


def _create_cycle_for_profile(
    conn: Connection,
    *,
    profile: Any,
    billing_period: date,
    deadline: datetime,
    pricing_effective_on: date | None = None,
) -> tuple[int, list[int]]:
    items, coverage, missing_subject_ids = _cycle_snapshot(
        conn,
        profile=profile,
        effective_on=(pricing_effective_on or deadline.astimezone(SCHOOL_TIMEZONE).date()),
    )
    if missing_subject_ids or not items:
        return 0, missing_subject_ids
    cycle_id = repository.insert_cycle(
        conn,
        profile_id=int(profile["id"]),
        student_id=int(profile["student_id"]),
        school_id=int(profile["school_id"]),
        billing_period=billing_period,
        due_at=deadline,
        pricing_mode=str(profile["pricing_mode"]),
        item_rows=items,
        coverage_rows=coverage,
    )
    return cycle_id, []


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
        existing = repository.get_cycle_by_profile_period_row(
            conn,
            profile_id=int(profile["id"]),
            billing_period=period,
        )
        cycle_id = int(existing["id"]) if existing else 0
        if not cycle_id:
            cycle_id, _missing_subject_ids = _create_cycle_for_profile(
                conn,
                profile=profile,
                billing_period=period,
                deadline=deadline,
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
    force_immediate_window: bool = False,
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
        if force_immediate_window or normalized_now > planned_issue_at
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
    repository.update_cycle_deadline(
        conn,
        cycle_id=cycle_id,
        deadline_at=deadline_at,
    )
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


def ensure_current_cycle_invoice(
    conn: Connection,
    *,
    profile: Any,
    now: datetime,
) -> int:
    """Repair an active schedule whose current cycle has no payable invoice."""

    normalized_now = now.astimezone(UTC)
    planned_period = next_billing_period(
        now=normalized_now,
        billing_day=int(profile["billing_day"]),
        starts_on=profile["starts_on"],
    )
    cycle = repository.get_profile_change_cycle_row(
        conn,
        profile_id=int(profile["id"]),
        planned_billing_period=planned_period,
        current_billing_period=_month_start(normalized_now.astimezone(SCHOOL_TIMEZONE).date()),
        for_update=True,
    )
    if cycle is None:
        cycle_id, missing_subject_ids = _create_cycle_for_profile(
            conn,
            profile=profile,
            billing_period=planned_period,
            deadline=cycle_deadline(planned_period, int(profile["billing_day"])),
            pricing_effective_on=normalized_now.astimezone(SCHOOL_TIMEZONE).date(),
        )
        if missing_subject_ids:
            raise BillingError(
                "Enter an amount for every active subject before issuing the invoice.",
                code="billing_subject_pricing_required",
                status_code=409,
            )
        if not cycle_id:
            raise BillingError(
                "The student needs an active subject enrollment before billing can be configured.",
                code="billing_enrollment_required",
                status_code=409,
            )
        cycle = repository.get_cycle_row(conn, cycle_id, for_update=True)
    else:
        cycle = repository.get_cycle_row(conn, int(cycle["id"]), for_update=True)

    if cycle["invoice_id"] is not None:
        return int(cycle["invoice_id"])
    if str(cycle["state"]) in {
        BillingCycleState.CANCELLED.value,
        BillingCycleState.SATISFIED.value,
        BillingCycleState.REVIEW_REQUIRED.value,
    }:
        return 0
    if repository.list_manual_candidate_rows(conn, int(cycle["id"])):
        repository.update_cycle_state(
            conn,
            cycle_id=int(cycle["id"]),
            state=BillingCycleState.REVIEW_REQUIRED.value,
        )
        return 0
    return issue_billing_cycle(
        conn,
        cycle_id=int(cycle["id"]),
        now=normalized_now,
        force_immediate_window=True,
    )


def apply_billing_profile_change(
    conn: Connection,
    *,
    profile: Any,
    apply_to: BillingScheduleApplyTo,
    actor: BillingAuditActor,
    is_first_configuration: bool,
    now: datetime,
) -> int:
    """Refresh an unissued cycle or audit-replace an eligible open invoice."""

    normalized_now = now.astimezone(UTC)
    planned_period = next_billing_period(
        now=normalized_now,
        billing_day=int(profile["billing_day"]),
        starts_on=profile["starts_on"],
    )
    current = repository.get_profile_change_cycle_row(
        conn,
        profile_id=int(profile["id"]),
        planned_billing_period=planned_period,
        current_billing_period=_month_start(normalized_now.astimezone(SCHOOL_TIMEZONE).date()),
        for_update=True,
    )
    if current and apply_to is BillingScheduleApplyTo.NEXT_CYCLE:
        return 0
    period = current["billing_period"] if current else planned_period
    if current:
        current = repository.get_cycle_row(conn, int(current["id"]), for_update=True)
        if str(current["state"]) == BillingCycleState.REVIEW_REQUIRED.value:
            raise BillingError(
                "Review the existing paid invoice before changing the current cycle.",
                code="billing_cycle_review_required",
                status_code=409,
            )
        if current["invoice_id"] is not None:
            invoice_status = InvoiceStatus(str(current["invoice_status"]))
            block_reason = ""
            if int(current["invoice_paid_minor"]) > 0 or invoice_status is InvoiceStatus.PAID:
                block_reason = "The current invoice already has a completed payment."
            elif bool(current["has_pending_payme"]):
                block_reason = "The current invoice has a pending Payme transaction."
            elif str(current["enforcement_state"] or "") == "held":
                block_reason = "The current invoice already placed accounts in payment-only mode."
            elif bool(current["has_active_review"]):
                block_reason = "The current billing cycle is under manual review."
            if block_reason:
                raise BillingError(
                    f"{block_reason} Apply the schedule from the next cycle.",
                    code="billing_current_cycle_locked",
                    status_code=409,
                )
            invoice_id = int(current["invoice_id"])
            if not ledger_repository.void_invoice(
                conn,
                invoice_id=invoice_id,
                expected_version=int(
                    ledger_repository.get_invoice_row(
                        conn,
                        invoice_id=invoice_id,
                        for_update=True,
                    )["version"]
                ),
                reason="Replaced by an audited billing schedule edit.",
            ):
                raise BillingError(
                    "The current invoice changed. Reload and try again.",
                    code="invoice_version_conflict",
                    status_code=409,
                )
            enforcement.reconcile_invoice_enforcement(
                conn,
                invoice_id=invoice_id,
                now=normalized_now,
            )
            ledger_repository.insert_audit_event(
                conn,
                event_type="finance.invoice_replaced_by_schedule",
                entity_type="invoice",
                entity_id=invoice_id,
                detail={"billing_cycle_id": int(current["id"])},
                staff_id=actor.staff_id,
                account_id=actor.account_id,
            )
        repository.supersede_cycle(conn, cycle_id=int(current["id"]))
    deadline = cycle_deadline(period, int(profile["billing_day"]))
    cycle_id, missing_subject_ids = _create_cycle_for_profile(
        conn,
        profile=profile,
        billing_period=period,
        deadline=deadline,
        pricing_effective_on=(
            normalized_now.astimezone(SCHOOL_TIMEZONE).date()
            if is_first_configuration or apply_to is BillingScheduleApplyTo.CURRENT_CYCLE
            else None
        ),
    )
    if missing_subject_ids:
        raise BillingError(
            "Enter an amount for every active subject before issuing the invoice.",
            code="billing_subject_pricing_required",
            status_code=409,
        )
    if not cycle_id:
        raise BillingError(
            "The student needs an active subject enrollment before billing can be configured.",
            code="billing_enrollment_required",
            status_code=409,
        )
    if current:
        repository.link_superseded_cycle(
            conn,
            cycle_id=int(current["id"]),
            replaced_by_cycle_id=cycle_id,
        )
    if repository.list_manual_candidate_rows(conn, cycle_id):
        repository.update_cycle_state(
            conn,
            cycle_id=cycle_id,
            state=BillingCycleState.REVIEW_REQUIRED.value,
        )
        return 0
    if is_first_configuration or apply_to is BillingScheduleApplyTo.CURRENT_CYCLE:
        return issue_billing_cycle(
            conn,
            cycle_id=cycle_id,
            now=normalized_now,
            force_immediate_window=True,
        )
    _enqueue_cycle_issuance(
        conn,
        cycle_id=cycle_id,
        cycle_version=1,
        issue_at=deadline - timedelta(hours=PAYMENT_WINDOW_HOURS),
        now=normalized_now,
    )
    return 0


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
    "apply_billing_profile_change",
    "cycle_deadline",
    "ensure_current_cycle_invoice",
    "issue_billing_cycle",
    "next_billing_period",
    "plan_billing_cycles",
    "review_manual_invoice",
    "reverse_manual_invoice_review",
]
