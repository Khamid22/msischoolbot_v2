"""Typed, transaction-bound read contract for parent payment views."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from backend.core.clock import SystemClock
from backend.core.time import SCHOOL_TIMEZONE
from backend.core.unit_of_work import Connection
from backend.modules.domains.finance import (
    billing_cycle_queries,
    billing_cycle_repository,
    billing_cycles,
    billing_profile_repository,
    commands,
    enforcement,
    enforcement_repository,
    ledger_repository,
    queries,
    repository,
)
from backend.modules.domains.finance.commands import BillingActor
from backend.modules.domains.finance.domain_types import (
    BillingAccountType,
    BillingCycleReviewDecision,
    BillingCycleReviewStatus,
    BillingCycleState,
    BillingItemStatus,
    BillingJobTopic,
    BillingProfileStatus,
    InvoiceKind,
    ManualPaymentMethod,
)
from backend.modules.domains.finance.policies import BillingError, major_to_minor
from backend.modules.domains.finance.queries import BillingSchoolScope
from backend.modules.domains.finance.schemas import (
    AddPaidStudentInvoiceCommand,
    BillingAccessStatus,
    BillingAccountDetail,
    BillingAccountPage,
    BillingAutomationStatus,
    BillingCycleReadiness,
    BillingCycleSummary,
    BillingItemInput,
    BillingProfileResult,
    ConfigureBillingProfileCommand,
    InvoiceDetail,
    InvoicePage,
    IssueStudentInvoiceCommand,
    RecordManualInvoicePaymentCommand,
    ReverseBillingCycleReviewCommand,
    ReverseInvoicePaymentCommand,
    ReviewBillingCycleInvoiceCommand,
    VoidStudentInvoiceCommand,
)
from backend.modules.domains.finance.service import payment_row_to_record
from backend.modules.jobs.contracts import enqueue_on_connection
from backend.modules.jobs.schemas import EnqueueJobCommand


@dataclass(frozen=True)
class PaymentRecord:
    payment_id: int
    invoice_id: int | None
    student_row_id: int
    subject: str
    month: str
    amount: float
    currency: str
    status: str
    state: str
    due_date: str
    paid_at: str
    notes: str
    balance: float
    can_pay_online: bool


@dataclass(frozen=True)
class CompatibilityPaymentRecord:
    payment_id: int
    student_id: int
    subject: str
    month_label: str
    amount: float
    currency: str
    status: str
    due_date: str
    paid_at: str
    notes: str
    version: int
    voided_at: str
    void_reason: str
    created_by_staff_id: int | None
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class BillingProfileItemCommand:
    group_id: int
    subject_id: int
    description: str
    amount_minor: int


@dataclass(frozen=True)
class EnsureStudentBillingProfileCommand:
    student_id: int
    school_id: int
    billing_parent_id: int | None
    billing_day: int
    starts_on: date
    items: tuple[BillingProfileItemCommand, ...]
    staff_id: int | None = None


def _payment_record_from_row(row) -> PaymentRecord:
    item = payment_row_to_record(row)
    payment_id = int(item["id"])
    is_invoice = payment_id >= repository.NEW_INVOICE_PAYMENT_ID_OFFSET
    is_outstanding = str(item["state"]) in {"debt", "due", "upcoming"}
    return PaymentRecord(
        payment_id=payment_id,
        invoice_id=(payment_id - repository.NEW_INVOICE_PAYMENT_ID_OFFSET if is_invoice else None),
        student_row_id=int(item["student_row_id"]),
        subject=str(item["subject"]),
        month=str(item["month"]),
        amount=float(item["amount"]),
        currency=str(item["currency"]),
        status=str(item["status"]),
        state=str(item["state"]),
        due_date=str(item["due_date"]),
        paid_at=str(item["paid_at"]),
        notes=str(item["notes"]),
        balance=float(item["amount"]) if is_outstanding else 0,
        can_pay_online=is_invoice and is_outstanding,
    )


def ensure_student_billing_profile(
    conn: Connection,
    command: EnsureStudentBillingProfileCommand,
) -> int:
    current = billing_profile_repository.get_billing_profile_row(
        conn,
        command.student_id,
        for_update=True,
    )
    expected_version = int(current["version"]) if current else None
    profile_id = billing_profile_repository.upsert_billing_profile(
        conn,
        student_id=command.student_id,
        school_id=command.school_id,
        billing_parent_id=command.billing_parent_id,
        billing_day=command.billing_day,
        starts_on=command.starts_on,
        status=BillingProfileStatus.ACTIVE,
        expected_version=expected_version,
        staff_id=command.staff_id,
    )
    if not profile_id:
        raise RuntimeError("The student billing profile could not be created.")
    billing_profile_repository.replace_billing_items(
        conn,
        profile_id=profile_id,
        starts_on=command.starts_on,
        items=[
            (
                item.group_id,
                item.subject_id,
                item.description,
                item.amount_minor,
            )
            for item in command.items
        ],
        staff_id=command.staff_id,
    )
    profile_version = int(current["version"]) + 1 if current else 1
    enqueue_on_connection(
        conn,
        EnqueueJobCommand(
            topic=BillingJobTopic.GENERATE_INVOICES.value,
            payload={
                "run_date": SystemClock().now().astimezone(SCHOOL_TIMEZONE).date().isoformat()
            },
            idempotency_key=(
                f"finance-generate-invoices:billing-profile:{profile_id}:v{profile_version}"
            ),
            max_attempts=10,
        ),
    )
    return profile_id


def list_payment_records(
    conn: Connection,
    *,
    student_row_id: int,
) -> tuple[PaymentRecord, ...]:
    return tuple(
        _payment_record_from_row(row)
        for row in repository.list_student_payment_rows(conn, student_row_id)
    )


def list_parent_payment_records(
    conn: Connection,
    *,
    parent_id: int,
    student_row_id: int | None = None,
) -> tuple[PaymentRecord, ...]:
    return tuple(
        _payment_record_from_row(row)
        for row in repository.list_parent_payment_rows(
            conn,
            parent_id=parent_id,
            student_row_id=student_row_id,
        )
    )


def parent_has_linked_student(
    conn: Connection,
    *,
    parent_id: int,
    student_row_id: int,
) -> bool:
    return repository.parent_has_linked_student_row(
        conn,
        parent_id=parent_id,
        student_row_id=student_row_id,
    )


def list_parent_billing_cycles(
    conn: Connection,
    *,
    parent_id: int,
    student_row_id: int | None = None,
) -> tuple[BillingCycleSummary, ...]:
    return tuple(
        billing_cycle_queries.cycle_summary(conn, row)
        for row in billing_cycle_repository.list_parent_cycle_rows(
            conn,
            parent_id=parent_id,
            student_row_id=student_row_id,
        )
    )


def list_student_account_payment_records(
    conn: Connection,
    *,
    student_id: int,
) -> tuple[PaymentRecord, ...]:
    return tuple(
        _payment_record_from_row(row)
        for row in repository.list_canonical_student_payment_rows(conn, student_id)
    )


def list_compatibility_payment_records(
    conn: Connection,
    *,
    student_id: int,
    student_row_id: int,
) -> tuple[CompatibilityPaymentRecord, ...]:
    records: list[CompatibilityPaymentRecord] = []
    for row in repository.list_student_payment_rows(conn, student_row_id):
        records.append(
            CompatibilityPaymentRecord(
                payment_id=int(row["id"]),
                student_id=int(student_id),
                subject=str(row["subject"] or ""),
                month_label=str(row["month_label"] or ""),
                amount=float(row["amount"] or 0),
                currency=str(row["currency"] or "UZS"),
                status=str(row["status"] or ""),
                due_date=str(row["due_date"] or ""),
                paid_at=str(row["paid_at"] or ""),
                notes=str(row["notes"] or ""),
                version=int(row.get("version") or 1),
                voided_at=str(row.get("voided_at") or ""),
                void_reason=str(row.get("void_reason") or ""),
                created_by_staff_id=(
                    int(row["created_by_admin_id"])
                    if row["created_by_admin_id"] is not None
                    else None
                ),
                created_at=str(row["created_at"] or ""),
                updated_at=str(row["updated_at"] or ""),
            )
        )
    return tuple(records)


def find_migrated_invoice_id(
    conn: Connection,
    *,
    legacy_payment_id: int,
) -> int | None:
    return ledger_repository.find_invoice_id_by_legacy_payment(
        conn,
        legacy_payment_id,
    )


def list_invoices(
    conn: Connection,
    *,
    scope: BillingSchoolScope,
    query: str = "",
    status: str = "all",
    origin: str = "all",
    enforcement: str = "all",
    school_id: int | None = None,
    billing_period: date | None = None,
    cursor: str | None = None,
    limit: int = 50,
) -> InvoicePage:
    return queries.list_invoices(
        conn,
        scope=scope,
        query=query,
        status=status,
        origin=origin,
        enforcement=enforcement,
        school_id=school_id,
        billing_period=billing_period,
        cursor=cursor,
        limit=limit,
    )


def list_billing_accounts(
    conn: Connection,
    *,
    scope: BillingSchoolScope,
    query: str = "",
    school_id: int | None = None,
    account_type: str = "all",
    schedule_status: str = "all",
    attention: str = "all",
    access: str = "all",
    cursor: str | None = None,
    limit: int = 25,
) -> BillingAccountPage:
    return queries.list_billing_accounts(
        conn,
        scope=scope,
        query=query,
        school_id=school_id,
        account_type=account_type,
        schedule_status=schedule_status,
        attention=attention,
        access=access,
        cursor=cursor,
        limit=limit,
    )


def get_billing_account(
    conn: Connection,
    *,
    scope: BillingSchoolScope,
    account_type: BillingAccountType,
    account_id: int,
) -> BillingAccountDetail:
    return queries.get_billing_account(
        conn,
        scope=scope,
        account_type=account_type,
        account_id=account_id,
    )


def get_invoice(
    conn: Connection,
    invoice_id: int,
    *,
    scope: BillingSchoolScope,
) -> InvoiceDetail:
    return queries.get_invoice(conn, invoice_id, scope=scope)


def issue_student_invoice(
    conn: Connection,
    command: IssueStudentInvoiceCommand,
    *,
    actor: BillingActor,
    scope: BillingSchoolScope,
) -> InvoiceDetail:
    return commands.issue_student_invoice(conn, command, actor=actor, scope=scope)


def add_paid_student_invoice(
    conn: Connection,
    command: AddPaidStudentInvoiceCommand,
    *,
    actor: BillingActor,
    scope: BillingSchoolScope,
) -> InvoiceDetail:
    return commands.add_paid_student_invoice(conn, command, actor=actor, scope=scope)


def record_manual_invoice_payment(
    conn: Connection,
    invoice_id: int,
    command: RecordManualInvoicePaymentCommand,
    *,
    actor: BillingActor,
    scope: BillingSchoolScope,
) -> InvoiceDetail:
    return commands.record_manual_payment(
        conn,
        invoice_id,
        command,
        actor=actor,
        scope=scope,
    )


def reverse_invoice_payment(
    conn: Connection,
    payment_id: int,
    command: ReverseInvoicePaymentCommand,
    *,
    actor: BillingActor,
    scope: BillingSchoolScope,
) -> InvoiceDetail:
    return commands.reverse_invoice_payment(
        conn,
        payment_id,
        command,
        actor=actor,
        scope=scope,
    )


def void_student_invoice(
    conn: Connection,
    invoice_id: int,
    command: VoidStudentInvoiceCommand,
    *,
    actor: BillingActor,
    scope: BillingSchoolScope,
) -> InvoiceDetail:
    return commands.void_student_invoice(
        conn,
        invoice_id,
        command,
        actor=actor,
        scope=scope,
    )


def get_billing_profile(
    conn: Connection,
    *,
    student_id: int,
    scope: BillingSchoolScope,
) -> BillingProfileResult | None:
    return queries.get_billing_profile(conn, student_id=student_id, scope=scope)


def get_billing_automation_status(
    conn: Connection,
    *,
    scope: BillingSchoolScope,
    now: datetime | None = None,
) -> BillingAutomationStatus:
    return queries.get_billing_automation_status(
        conn,
        scope=scope,
        now=now,
    )


def get_billing_cycle_readiness(
    conn: Connection,
    *,
    scope: BillingSchoolScope,
    now: datetime | None = None,
) -> BillingCycleReadiness:
    return billing_cycle_queries.get_billing_cycle_readiness(
        conn,
        scope=scope,
        now=now,
    )


def review_billing_cycle_invoice(
    conn: Connection,
    command: ReviewBillingCycleInvoiceCommand,
    *,
    actor: BillingActor,
    scope: BillingSchoolScope,
) -> BillingCycleSummary:
    return billing_cycles.review_manual_invoice(
        conn,
        command,
        actor=actor,
        scope=scope,
    )


def reverse_billing_cycle_review(
    conn: Connection,
    review_id: int,
    command: ReverseBillingCycleReviewCommand,
    *,
    actor: BillingActor,
    scope: BillingSchoolScope,
) -> BillingCycleSummary:
    return billing_cycles.reverse_manual_invoice_review(
        conn,
        review_id,
        command,
        actor=actor,
        scope=scope,
    )


def configure_billing_profile(
    conn: Connection,
    command: ConfigureBillingProfileCommand,
    *,
    actor: BillingActor,
    scope: BillingSchoolScope,
) -> BillingProfileResult:
    return commands.configure_billing_profile(conn, command, actor=actor, scope=scope)


def parent_invoice_checkout_data(
    conn: Connection,
    *,
    parent_id: int,
    invoice_id: int,
) -> tuple[int, str]:
    return queries.parent_invoice_checkout_data(
        conn,
        parent_id=parent_id,
        invoice_id=invoice_id,
    )


def get_account_billing_access(
    conn: Connection,
    *,
    account_id: int,
    now: datetime | None = None,
) -> BillingAccessStatus:
    return enforcement.account_billing_access(
        conn,
        account_id=account_id,
        now=now or SystemClock().now(),
    )


def account_has_billing_hold(conn: Connection, *, account_id: int) -> bool:
    return enforcement_repository.account_has_active_hold(conn, account_id)


def student_invoice_checkout_data(
    conn: Connection,
    *,
    student_id: int,
    invoice_id: int,
) -> tuple[int, str]:
    return enforcement.student_invoice_checkout_data(
        conn,
        student_id=student_id,
        invoice_id=invoice_id,
    )


__all__ = [
    "AddPaidStudentInvoiceCommand",
    "BillingActor",
    "BillingAccountDetail",
    "BillingAccountPage",
    "BillingAccountType",
    "BillingAccessStatus",
    "BillingAutomationStatus",
    "BillingCycleReadiness",
    "BillingCycleReviewDecision",
    "BillingCycleReviewStatus",
    "BillingCycleState",
    "BillingCycleSummary",
    "BillingError",
    "BillingProfileItemCommand",
    "BillingProfileResult",
    "BillingSchoolScope",
    "BillingItemInput",
    "BillingItemStatus",
    "CompatibilityPaymentRecord",
    "ConfigureBillingProfileCommand",
    "EnsureStudentBillingProfileCommand",
    "InvoiceDetail",
    "InvoiceKind",
    "InvoicePage",
    "IssueStudentInvoiceCommand",
    "ManualPaymentMethod",
    "PaymentRecord",
    "RecordManualInvoicePaymentCommand",
    "ReviewBillingCycleInvoiceCommand",
    "ReverseBillingCycleReviewCommand",
    "ReverseInvoicePaymentCommand",
    "VoidStudentInvoiceCommand",
    "add_paid_student_invoice",
    "account_has_billing_hold",
    "configure_billing_profile",
    "ensure_student_billing_profile",
    "find_migrated_invoice_id",
    "get_billing_profile",
    "get_billing_account",
    "get_billing_automation_status",
    "get_billing_cycle_readiness",
    "get_account_billing_access",
    "get_invoice",
    "issue_student_invoice",
    "list_compatibility_payment_records",
    "list_invoices",
    "list_billing_accounts",
    "list_payment_records",
    "list_parent_billing_cycles",
    "list_parent_payment_records",
    "list_student_account_payment_records",
    "major_to_minor",
    "parent_invoice_checkout_data",
    "parent_has_linked_student",
    "record_manual_invoice_payment",
    "reverse_invoice_payment",
    "review_billing_cycle_invoice",
    "reverse_billing_cycle_review",
    "student_invoice_checkout_data",
    "void_student_invoice",
]
