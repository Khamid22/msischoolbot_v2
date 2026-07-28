"""Typed, transaction-bound read contract for parent payment views."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from backend.core.clock import SystemClock
from backend.core.unit_of_work import Connection
from backend.modules.domains.finance import (
    billing_profile_repository,
    commands,
    enforcement,
    enforcement_repository,
    ledger_repository,
    queries,
    repository,
)
from backend.modules.domains.finance.domain_types import (
    BillingProfileStatus,
    InvoiceKind,
    ManualPaymentMethod,
)
from backend.modules.domains.finance.policies import BillingError, major_to_minor
from backend.modules.domains.finance.queries import BillingSchoolScope
from backend.modules.domains.finance.schemas import (
    AddPaidStudentInvoiceCommand,
    BillingAccessStatus,
    BillingItemInput,
    BillingProfileResult,
    ConfigureBillingProfileCommand,
    InvoiceDetail,
    InvoicePage,
    IssueStudentInvoiceCommand,
    RecordManualInvoicePaymentCommand,
    ReverseInvoicePaymentCommand,
    VoidStudentInvoiceCommand,
)
from backend.modules.domains.finance.service import payment_row_to_record


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
        invoice_id=(
            payment_id - repository.NEW_INVOICE_PAYMENT_ID_OFFSET
            if is_invoice
            else None
        ),
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


BillingActor = commands.BillingActor


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
    return queries.list_invoices(
        conn,
        scope=scope,
        query=query,
        status=status,
        origin=origin,
        enforcement=enforcement,
        limit=limit,
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
    "BillingAccessStatus",
    "BillingError",
    "BillingProfileItemCommand",
    "BillingProfileResult",
    "BillingSchoolScope",
    "BillingItemInput",
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
    "ReverseInvoicePaymentCommand",
    "VoidStudentInvoiceCommand",
    "add_paid_student_invoice",
    "account_has_billing_hold",
    "configure_billing_profile",
    "ensure_student_billing_profile",
    "find_migrated_invoice_id",
    "get_billing_profile",
    "get_account_billing_access",
    "get_invoice",
    "issue_student_invoice",
    "list_compatibility_payment_records",
    "list_invoices",
    "list_payment_records",
    "list_student_account_payment_records",
    "major_to_minor",
    "parent_invoice_checkout_data",
    "record_manual_invoice_payment",
    "reverse_invoice_payment",
    "student_invoice_checkout_data",
    "void_student_invoice",
]
