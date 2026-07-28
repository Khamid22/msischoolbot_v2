"""Transaction-bound commands for invoices, settlements, and billing profiles."""

from __future__ import annotations

from dataclasses import dataclass

from backend.core.clock import SystemClock
from backend.core.unit_of_work import Connection
from backend.modules.domains.finance import billing_profile_repository
from backend.modules.domains.finance import enforcement
from backend.modules.domains.finance import ledger_repository as repository
from backend.modules.domains.finance.domain_types import PaymentStatus
from backend.modules.domains.finance.policies import (
    BillingError,
    ensure_invoice_accepts_payment,
    ensure_invoice_can_be_voided,
    ensure_payment_can_be_reversed,
)
from backend.modules.domains.finance.queries import (
    BillingSchoolScope,
    get_billing_profile,
    get_invoice,
)
from backend.modules.domains.finance.schemas import (
    AddPaidStudentInvoiceCommand,
    BillingProfileResult,
    ConfigureBillingProfileCommand,
    InvoiceDetail,
    IssueStudentInvoiceCommand,
    RecordManualInvoicePaymentCommand,
    ReverseInvoicePaymentCommand,
    VoidStudentInvoiceCommand,
)


@dataclass(frozen=True)
class BillingActor:
    staff_id: int | None
    account_id: int | None


def _student_for_write(
    conn: Connection,
    *,
    student_id: int,
    expected_version: int,
    scope: BillingSchoolScope,
) -> object:
    row = repository.get_scoped_student_row(
        conn,
        student_id=student_id,
        school_ids=scope.school_ids,
        all_schools=scope.all_schools,
        for_update=True,
    )
    if not row:
        raise BillingError("Student was not found.", code="student_not_found", status_code=404)
    if str(row["status"]) != "active":
        raise BillingError("Only an active student can receive a new invoice.")
    if int(row["version"]) != int(expected_version):
        raise BillingError(
            "The student changed. Reload and try again.",
            code="student_version_conflict",
            status_code=409,
        )
    return row


def issue_student_invoice(
    conn: Connection,
    command: IssueStudentInvoiceCommand,
    *,
    actor: BillingActor,
    scope: BillingSchoolScope,
) -> InvoiceDetail:
    _student_for_write(
        conn,
        student_id=command.student_id,
        expected_version=command.expected_student_version,
        scope=scope,
    )
    enrollment = repository.find_active_enrollment_row(
        conn,
        student_id=command.student_id,
        subject_id=command.subject_id,
    )
    if not enrollment:
        raise BillingError("The student is not actively enrolled in this subject.")
    parent_id = repository.find_billing_parent_id(conn, command.student_id)
    invoice_id = repository.insert_student_invoice(
        conn,
        student_id=command.student_id,
        parent_id=parent_id,
        group_id=int(enrollment["group_id"]),
        subject_id=int(enrollment["subject_id"]),
        description=command.description,
        amount_minor=command.amount_minor,
        due_date=command.due_date,
        billing_period=command.billing_period,
        invoice_kind=command.invoice_kind,
        staff_id=actor.staff_id,
    )
    repository.insert_audit_event(
        conn,
        event_type="finance.invoice_issued",
        entity_type="invoice",
        entity_id=invoice_id,
        detail={
            "student_id": command.student_id,
            "amount_minor": command.amount_minor,
            "currency": "UZS",
        },
        staff_id=actor.staff_id,
        account_id=actor.account_id,
    )
    enforcement.start_invoice_enforcement(
        conn,
        invoice_id=invoice_id,
        now=SystemClock().now(),
    )
    return get_invoice(conn, invoice_id, scope=scope)


def record_manual_payment(
    conn: Connection,
    invoice_id: int,
    command: RecordManualInvoicePaymentCommand,
    *,
    actor: BillingActor,
    scope: BillingSchoolScope,
) -> InvoiceDetail:
    invoice = get_invoice(conn, invoice_id, scope=scope, for_update=True)
    if invoice.version != command.expected_version:
        raise BillingError(
            "The invoice changed. Reload and try again.",
            code="invoice_version_conflict",
            status_code=409,
        )
    ensure_invoice_accepts_payment(invoice.status)
    if command.amount_minor > invoice.balance_minor:
        raise BillingError("Payment amount cannot exceed the invoice balance.")
    if repository.find_pending_payme_transaction(conn, invoice_id):
        raise BillingError(
            "A Payme transaction is pending for this invoice.",
            code="payme_transaction_pending",
            status_code=409,
        )
    payment_id = repository.insert_manual_payment(
        conn,
        invoice_id=invoice_id,
        amount_minor=command.amount_minor,
        method=command.method,
        paid_at=command.paid_at,
        reference=command.reference,
        reason=command.reason,
        staff_id=actor.staff_id,
    )
    repository.recompute_invoice_settlement(conn, invoice_id)
    enforcement.reconcile_invoice_enforcement(
        conn,
        invoice_id=invoice_id,
        now=SystemClock().now(),
    )
    repository.insert_audit_event(
        conn,
        event_type="finance.manual_payment_recorded",
        entity_type="invoice_payment",
        entity_id=payment_id,
        detail={
            "invoice_id": invoice_id,
            "amount_minor": command.amount_minor,
            "method": command.method.value,
            "reference": command.reference,
        },
        staff_id=actor.staff_id,
        account_id=actor.account_id,
    )
    return get_invoice(conn, invoice_id, scope=scope)


def add_paid_student_invoice(
    conn: Connection,
    command: AddPaidStudentInvoiceCommand,
    *,
    actor: BillingActor,
    scope: BillingSchoolScope,
) -> InvoiceDetail:
    invoice = issue_student_invoice(conn, command, actor=actor, scope=scope)
    return record_manual_payment(
        conn,
        invoice.invoice_id,
        RecordManualInvoicePaymentCommand(
            amount_minor=command.amount_minor,
            method=command.method,
            paid_at=command.paid_at,
            reference=command.reference,
            reason=command.reason,
            expected_version=invoice.version,
        ),
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
    payment = repository.get_payment_row(conn, payment_id=payment_id, for_update=True)
    if not payment:
        raise BillingError("Payment was not found.", code="payment_not_found", status_code=404)
    invoice = get_invoice(
        conn,
        int(payment["invoice_id"]),
        scope=scope,
        for_update=True,
    )
    if invoice.version != command.expected_invoice_version:
        raise BillingError(
            "The invoice changed. Reload and try again.",
            code="invoice_version_conflict",
            status_code=409,
        )
    ensure_payment_can_be_reversed(PaymentStatus(str(payment["status"])))
    if str(payment["source"]) != "manual":
        raise BillingError("Payme payments must be refunded through Payme.")
    if not repository.reverse_payment(
        conn,
        payment_id=payment_id,
        reason=command.reason,
        staff_id=actor.staff_id,
    ):
        raise BillingError("Payment changed. Reload and try again.", status_code=409)
    repository.recompute_invoice_settlement(conn, invoice.invoice_id)
    enforcement.reconcile_invoice_enforcement(
        conn,
        invoice_id=invoice.invoice_id,
        now=SystemClock().now(),
    )
    repository.insert_audit_event(
        conn,
        event_type="finance.manual_payment_reversed",
        entity_type="invoice_payment",
        entity_id=payment_id,
        detail={"invoice_id": invoice.invoice_id, "reason": command.reason},
        staff_id=actor.staff_id,
        account_id=actor.account_id,
    )
    return get_invoice(conn, invoice.invoice_id, scope=scope)


def void_student_invoice(
    conn: Connection,
    invoice_id: int,
    command: VoidStudentInvoiceCommand,
    *,
    actor: BillingActor,
    scope: BillingSchoolScope,
) -> InvoiceDetail:
    invoice = get_invoice(conn, invoice_id, scope=scope, for_update=True)
    ensure_invoice_can_be_voided(invoice.status, invoice.paid_minor)
    if not repository.void_invoice(
        conn,
        invoice_id=invoice_id,
        expected_version=command.expected_version,
        reason=command.reason,
    ):
        raise BillingError(
            "The invoice changed. Reload and try again.",
            code="invoice_version_conflict",
            status_code=409,
        )
    repository.insert_audit_event(
        conn,
        event_type="finance.invoice_voided",
        entity_type="invoice",
        entity_id=invoice_id,
        detail={"reason": command.reason},
        staff_id=actor.staff_id,
        account_id=actor.account_id,
    )
    enforcement.reconcile_invoice_enforcement(
        conn,
        invoice_id=invoice_id,
        now=SystemClock().now(),
    )
    return get_invoice(conn, invoice_id, scope=scope)


def configure_billing_profile(
    conn: Connection,
    command: ConfigureBillingProfileCommand,
    *,
    actor: BillingActor,
    scope: BillingSchoolScope,
) -> BillingProfileResult:
    student = repository.get_scoped_student_row(
        conn,
        student_id=command.student_id,
        school_ids=scope.school_ids,
        all_schools=scope.all_schools,
        for_update=True,
    )
    if not student:
        raise BillingError("Student was not found.", code="student_not_found", status_code=404)
    normalized_items: list[tuple[int, int, str, int]] = []
    seen_groups: set[int] = set()
    for item in command.items:
        if item.group_id in seen_groups:
            raise BillingError("A billing group can appear only once.")
        seen_groups.add(item.group_id)
        row = repository.find_active_group_enrollment_row(
            conn,
            student_id=command.student_id,
            group_id=item.group_id,
        )
        if not row:
            raise BillingError("Every billing item must use an active student group.")
        description = item.description.strip() or str(row["subject_name"])
        normalized_items.append(
            (
                int(row["group_id"]),
                int(row["subject_id"]),
                description,
                item.amount_minor,
            )
        )
    profile_id = billing_profile_repository.upsert_billing_profile(
        conn,
        student_id=command.student_id,
        school_id=int(student["school_id"]),
        billing_parent_id=repository.find_billing_parent_id(conn, command.student_id),
        billing_day=command.billing_day,
        starts_on=command.starts_on,
        status=command.status,
        expected_version=command.expected_version,
        staff_id=actor.staff_id,
    )
    if not profile_id:
        raise BillingError(
            "The billing profile changed. Reload and try again.",
            code="billing_profile_version_conflict",
            status_code=409,
        )
    billing_profile_repository.replace_billing_items(
        conn,
        profile_id=profile_id,
        starts_on=command.starts_on,
        items=normalized_items,
    )
    repository.insert_audit_event(
        conn,
        event_type="finance.billing_profile_configured",
        entity_type="student_billing_profile",
        entity_id=profile_id,
        detail={
            "student_id": command.student_id,
            "billing_day": command.billing_day,
            "status": command.status.value,
            "group_ids": sorted(seen_groups),
        },
        staff_id=actor.staff_id,
        account_id=actor.account_id,
    )
    profile = get_billing_profile(conn, student_id=command.student_id, scope=scope)
    if profile is None:
        raise BillingError("Billing profile could not be loaded.")
    return profile


__all__ = [
    "BillingActor",
    "add_paid_student_invoice",
    "configure_billing_profile",
    "issue_student_invoice",
    "record_manual_payment",
    "reverse_invoice_payment",
    "void_student_invoice",
]
