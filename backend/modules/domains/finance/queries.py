"""Typed read contracts for invoices and billing profiles."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from backend.core.clock import SystemClock
from backend.core.time import SCHOOL_TIMEZONE
from backend.core.unit_of_work import Connection
from backend.modules.domains.finance import (
    automation_repository,
    billing_profile_repository,
    enforcement_repository,
)
from backend.modules.domains.finance import ledger_repository as repository
from backend.modules.domains.finance.domain_types import (
    BillingAutomationWorkerState,
    BillingEnforcementState,
    BillingItemStatus,
    BillingNotificationDeliveryStatus,
    BillingNotificationStage,
    BillingProfileStatus,
    InvoiceKind,
    InvoiceOrigin,
    InvoiceStatus,
    PaymentSource,
    PaymentStatus,
)
from backend.modules.domains.finance.policies import BillingError
from backend.modules.domains.finance.schemas import (
    BillingAutomationStatus,
    BillingNotificationTimelineEntry,
    BillingProfileItemResult,
    BillingProfileResult,
    InvoiceDetail,
    InvoiceLineResult,
    InvoicePage,
    InvoicePaymentResult,
    InvoiceSummary,
)

WORKER_STALL_THRESHOLD = timedelta(minutes=30)


@dataclass(frozen=True)
class BillingSchoolScope:
    school_ids: frozenset[int] = frozenset()
    all_schools: bool = False

    def allows(self, school_id: int) -> bool:
        return self.all_schools or int(school_id) in self.school_ids


def _invoice_summary(row: Mapping[str, Any]) -> InvoiceSummary:
    values = dict(row)
    return InvoiceSummary(
        invoice_id=int(values["id"]),
        invoice_number=str(values["invoice_number"]),
        admission_id=(
            int(values["admission_id"]) if values.get("admission_id") is not None else None
        ),
        student_id=(int(values["student_id"]) if values.get("student_id") is not None else None),
        student_row_id=(
            int(values["legacy_student_row_id"])
            if values.get("legacy_student_row_id") is not None
            else None
        ),
        student_name=str(values.get("student_name") or ""),
        student_code=str(values.get("student_code") or ""),
        parent_name=str(values.get("parent_name") or ""),
        school_id=int(values["school_id"]),
        school_name=str(values["school_name"]),
        invoice_kind=InvoiceKind(str(values["invoice_kind"])),
        origin=InvoiceOrigin(str(values.get("origin") or "admission")),
        billing_period=values["billing_period"],
        currency=str(values["currency"]),
        total_minor=int(values["total_minor"]),
        paid_minor=int(values["paid_minor"]),
        balance_minor=int(values["total_minor"]) - int(values["paid_minor"]),
        status=InvoiceStatus(str(values["status"])),
        due_date=values["due_date"],
        issued_at=values.get("issued_at"),
        paid_at=values.get("paid_at"),
        enforcement_state=(
            BillingEnforcementState(str(values["enforcement_state"]))
            if values.get("enforcement_state")
            else None
        ),
        countdown_started_at=values.get("countdown_started_at"),
        payment_deadline_at=values.get("payment_deadline_at"),
        version=int(values["version"]),
    )


def _timeline_status(
    *,
    counts: Mapping[str, int],
    schedule_state: BillingEnforcementState,
) -> BillingNotificationDeliveryStatus:
    if counts.get("failed", 0):
        return BillingNotificationDeliveryStatus.FAILED
    if counts.get("pending", 0):
        return BillingNotificationDeliveryStatus.PENDING
    if counts.get("sent", 0):
        return BillingNotificationDeliveryStatus.SENT
    if counts.get("skipped", 0):
        return BillingNotificationDeliveryStatus.SKIPPED
    if schedule_state in {
        BillingEnforcementState.CLEARED,
        BillingEnforcementState.CANCELLED,
    }:
        return BillingNotificationDeliveryStatus.CANCELLED
    return BillingNotificationDeliveryStatus.SCHEDULED


def _notification_timeline(
    conn: Connection,
    *,
    invoice_id: int,
) -> list[BillingNotificationTimelineEntry]:
    schedule = enforcement_repository.get_schedule_by_invoice_row(conn, invoice_id)
    if not schedule:
        return []
    counts_by_stage: dict[str, dict[str, int]] = {}
    first_created_by_stage: dict[str, datetime] = {}
    for row in enforcement_repository.list_notification_delivery_summary_rows(
        conn,
        schedule_id=int(schedule["id"]),
    ):
        stage = str(row["stage"])
        counts_by_stage.setdefault(stage, {})[str(row["status"])] = int(row["delivery_count"])
        if row["first_created_at"] is not None:
            first_created_by_stage[stage] = row["first_created_at"]
    deadline_at = schedule["deadline_at"]
    scheduled_times = {
        BillingNotificationStage.INITIAL: schedule["countdown_started_at"],
        BillingNotificationStage.TWENTY_FOUR_HOURS: deadline_at - timedelta(hours=24),
        BillingNotificationStage.SIX_HOURS: deadline_at - timedelta(hours=6),
        BillingNotificationStage.HELD: deadline_at,
    }
    if BillingNotificationStage.RESTORED.value in counts_by_stage:
        scheduled_times[BillingNotificationStage.RESTORED] = (
            first_created_by_stage.get(BillingNotificationStage.RESTORED.value)
            or schedule["cleared_at"]
            or schedule["updated_at"]
        )
    schedule_state = BillingEnforcementState(str(schedule["state"]))
    timeline: list[BillingNotificationTimelineEntry] = []
    for stage, scheduled_for in scheduled_times.items():
        counts = counts_by_stage.get(stage.value, {})
        timeline.append(
            BillingNotificationTimelineEntry(
                stage=stage,
                scheduled_for=scheduled_for,
                status=_timeline_status(
                    counts=counts,
                    schedule_state=schedule_state,
                ),
                recipient_count=sum(counts.values()),
                pending_count=counts.get("pending", 0),
                sent_count=counts.get("sent", 0),
                skipped_count=counts.get("skipped", 0),
                failed_count=counts.get("failed", 0),
            )
        )
    return timeline


def list_invoices(
    conn: Connection,
    *,
    scope: BillingSchoolScope,
    query: str = "",
    status: str = "all",
    origin: str = "all",
    enforcement: str = "all",
    limit: int = 50,
) -> InvoicePage:
    allowed_statuses = {"all", *(item.value for item in InvoiceStatus)}
    allowed_origins = {"all", *(item.value for item in InvoiceOrigin)}
    allowed_enforcement_states = {
        "all",
        "not_scheduled",
        *(item.value for item in BillingEnforcementState),
    }
    if status not in allowed_statuses:
        raise BillingError("Invoice status filter is invalid.")
    if origin not in allowed_origins:
        raise BillingError("Invoice origin filter is invalid.")
    if enforcement not in allowed_enforcement_states:
        raise BillingError("Billing enforcement filter is invalid.")
    rows = repository.list_scoped_invoice_rows(
        conn,
        school_ids=scope.school_ids,
        all_schools=scope.all_schools,
        query=query,
        status=status,
        origin=origin,
        enforcement=enforcement,
        limit=limit,
    )
    return InvoicePage(
        items=[_invoice_summary(row) for row in rows],
        total=int(rows[0]["total_count"]) if rows else 0,
    )


def get_invoice(
    conn: Connection,
    invoice_id: int,
    *,
    scope: BillingSchoolScope,
    for_update: bool = False,
) -> InvoiceDetail:
    row = repository.get_invoice_row(
        conn,
        invoice_id=invoice_id,
        for_update=for_update,
    )
    if not row or not scope.allows(int(row["school_id"])):
        raise BillingError("Invoice was not found.", code="invoice_not_found", status_code=404)
    summary = _invoice_summary(row)
    lines = [
        InvoiceLineResult(
            line_id=int(line["id"]),
            group_id=int(line["group_id"]) if line["group_id"] is not None else None,
            subject_id=(int(line["subject_id"]) if line["subject_id"] is not None else None),
            description=str(line["description"]),
            amount_minor=int(line["amount_minor"]),
        )
        for line in repository.list_invoice_line_rows(conn, invoice_id)
    ]
    payments = [
        InvoicePaymentResult(
            payment_id=int(payment["id"]),
            source=PaymentSource(str(payment["source"])),
            method=str(payment["method"]),
            amount_minor=int(payment["amount_minor"]),
            currency=str(payment["currency"]),
            status=PaymentStatus(str(payment["status"])),
            reference=str(payment["reference"]),
            reason=str(payment["reason"]),
            paid_at=payment["paid_at"],
            reversed_at=payment["reversed_at"],
            reversal_reason=str(payment["reversal_reason"]),
        )
        for payment in repository.list_invoice_payment_rows(conn, invoice_id)
    ]
    return InvoiceDetail(
        **summary.model_dump(),
        lines=lines,
        payments=payments,
        notification_timeline=_notification_timeline(
            conn,
            invoice_id=invoice_id,
        ),
        void_reason=str(row["void_reason"]),
    )


def get_billing_automation_status(
    conn: Connection,
    *,
    scope: BillingSchoolScope,
    now: datetime | None = None,
) -> BillingAutomationStatus:
    generated_at = now or SystemClock().now()
    row = automation_repository.get_automation_status_row(
        conn,
        school_ids=scope.school_ids,
        all_schools=scope.all_schools,
        school_date=generated_at.astimezone(SCHOOL_TIMEZONE).date(),
    )
    if not row:
        raise BillingError("Billing automation status could not be loaded.")
    last_completed_at = row["last_completed_at"]
    if last_completed_at is None:
        worker_state = BillingAutomationWorkerState.NOT_STARTED
    elif generated_at - last_completed_at > WORKER_STALL_THRESHOLD:
        worker_state = BillingAutomationWorkerState.STALLED
    else:
        worker_state = BillingAutomationWorkerState.HEALTHY
    return BillingAutomationStatus(
        generated_at=generated_at,
        effective_school_ids=sorted(scope.school_ids),
        all_schools=scope.all_schools,
        active_billing_profiles=int(row["active_billing_profiles"]),
        currently_due_billing_profiles=int(row["currently_due_billing_profiles"]),
        open_invoices=int(row["open_invoices"]),
        open_invoices_without_enforcement=int(row["open_invoices_without_enforcement"]),
        linked_telegram_recipients=int(row["linked_telegram_recipients"]),
        unlinked_telegram_recipients=int(row["unlinked_telegram_recipients"]),
        pending_notification_deliveries=int(row["pending_notification_deliveries"]),
        failed_notification_deliveries=int(row["failed_notification_deliveries"]),
        active_payment_only_holds=int(row["active_payment_only_holds"]),
        pending_finance_jobs=int(row["pending_job_count"]),
        worker_state=worker_state,
        last_successful_finance_worker_at=last_completed_at,
    )


def get_billing_profile(
    conn: Connection,
    *,
    student_id: int,
    scope: BillingSchoolScope,
) -> BillingProfileResult | None:
    row = billing_profile_repository.get_billing_profile_row(conn, student_id)
    if not row:
        return None
    if not scope.allows(int(row["school_id"])):
        raise BillingError(
            "Billing profile was not found.",
            code="billing_profile_not_found",
            status_code=404,
        )
    items = [
        BillingProfileItemResult(
            item_id=int(item["id"]),
            group_id=int(item["group_id"]),
            group_name=str(item["group_name"]),
            subject_id=int(item["subject_id"]),
            subject_name=str(item["subject_name"]),
            description=str(item["description"]),
            amount_minor=int(item["amount_minor"]),
            active_from=item["active_from"],
            active_until=item["active_until"],
            status=BillingItemStatus(str(item["status"])),
            cancelled_at=item["cancelled_at"],
            cancellation_reason=str(item["cancellation_reason"]),
        )
        for item in billing_profile_repository.list_billing_item_rows(
            conn,
            int(row["id"]),
        )
    ]
    return BillingProfileResult(
        profile_id=int(row["id"]),
        student_id=int(row["student_id"]),
        school_id=int(row["school_id"]),
        billing_parent_id=(int(row["billing_parent_id"]) if row["billing_parent_id"] else None),
        billing_day=int(row["billing_day"]),
        currency=str(row["currency"]),
        starts_on=row["starts_on"],
        ends_on=row["ends_on"],
        status=BillingProfileStatus(str(row["status"])),
        version=int(row["version"]),
        items=items,
    )


def parent_can_access_invoice(
    conn: Connection,
    *,
    parent_id: int,
    invoice_id: int,
) -> bool:
    return repository.parent_has_invoice_access(
        conn,
        parent_id=parent_id,
        invoice_id=invoice_id,
    )


def parent_invoice_checkout_data(
    conn: Connection,
    *,
    parent_id: int,
    invoice_id: int,
) -> tuple[int, str]:
    if not parent_can_access_invoice(conn, parent_id=parent_id, invoice_id=invoice_id):
        raise BillingError("Invoice was not found.", code="invoice_not_found", status_code=404)
    row = repository.get_invoice_row(conn, invoice_id=invoice_id)
    if not row:
        raise BillingError("Invoice was not found.", code="invoice_not_found", status_code=404)
    if str(row["status"]) not in {"issued", "partially_paid", "overdue"}:
        raise BillingError("This invoice is not payable.")
    balance_minor = int(row["total_minor"]) - int(row["paid_minor"])
    if balance_minor <= 0:
        raise BillingError("This invoice has no outstanding balance.")
    return balance_minor, str(row["currency"])


def invoice_state_for_parent(status: InvoiceStatus, due_date: date) -> str:
    if status is InvoiceStatus.PAID:
        return "paid"
    if status is InvoiceStatus.VOIDED:
        return "voided"
    if due_date < date.today():
        return "debt"
    if due_date > date.today():
        return "upcoming"
    return "due"


__all__ = [
    "BillingSchoolScope",
    "get_billing_profile",
    "get_billing_automation_status",
    "get_invoice",
    "invoice_state_for_parent",
    "list_invoices",
    "parent_can_access_invoice",
    "parent_invoice_checkout_data",
]
