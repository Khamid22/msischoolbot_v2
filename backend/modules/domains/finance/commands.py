"""Transaction-bound commands for invoices, settlements, and billing profiles."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from psycopg.errors import CheckViolation, UniqueViolation

from backend.core.clock import SystemClock
from backend.core.time import SCHOOL_TIMEZONE
from backend.core.unit_of_work import Connection
from backend.modules.domains.finance import (
    billing_cycle_repository,
    billing_cycles,
    billing_profile_repository,
    enforcement,
)
from backend.modules.domains.finance import ledger_repository as repository
from backend.modules.domains.finance.domain_types import (
    BillingJobTopic,
    BillingPricingMode,
    BillingProfileStatus,
    BillingScheduleApplyTo,
    PaymentStatus,
)
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
    ReviewBillingCycleInvoiceCommand,
    VoidStudentInvoiceCommand,
)
from backend.modules.jobs.contracts import enqueue_on_connection
from backend.modules.jobs.schemas import EnqueueJobCommand


@dataclass(frozen=True)
class BillingActor:
    staff_id: int | None
    account_id: int | None


def _enqueue_invoice_generation_check(
    conn: Connection,
    *,
    profile_id: int,
    profile_version: int,
) -> None:
    run_date = SystemClock().now().astimezone(SCHOOL_TIMEZONE).date()
    enqueue_on_connection(
        conn,
        EnqueueJobCommand(
            topic=BillingJobTopic.GENERATE_INVOICES.value,
            payload={"run_date": run_date.isoformat()},
            idempotency_key=(
                f"finance-generate-invoices:billing-profile:{profile_id}:v{profile_version}"
            ),
            max_attempts=10,
        ),
    )


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
    paid_invoice = record_manual_payment(
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
    if (
        command.billing_cycle_id is not None
        and command.billing_treatment is not None
        and command.expected_cycle_version is not None
    ):
        billing_cycles.review_manual_invoice(
            conn,
            ReviewBillingCycleInvoiceCommand(
                cycle_id=command.billing_cycle_id,
                invoice_id=paid_invoice.invoice_id,
                decision=command.billing_treatment,
                allocated_minor=(
                    command.amount_minor if command.billing_treatment.value == "apply" else 0
                ),
                reason=command.reason,
                expected_cycle_version=command.expected_cycle_version,
            ),
            actor=actor,
            scope=scope,
        )
    return get_invoice(conn, paid_invoice.invoice_id, scope=scope)


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
    now = SystemClock().now()
    student = repository.get_scoped_student_row(
        conn,
        student_id=command.student_id,
        school_ids=scope.school_ids,
        all_schools=scope.all_schools,
        for_update=True,
    )
    if not student:
        raise BillingError("Student was not found.", code="student_not_found", status_code=404)
    enrollment_rows = billing_cycle_repository.list_active_enrollment_rows(
        conn,
        student_id=command.student_id,
    )
    if not enrollment_rows:
        raise BillingError(
            "The student needs an active subject enrollment before billing can be configured.",
            code="billing_enrollment_required",
            status_code=409,
        )
    enrollment_by_group = {int(row["group_id"]): row for row in enrollment_rows}
    enrollment_by_subject: dict[int, Any] = {}
    for row in enrollment_rows:
        enrollment_by_subject.setdefault(int(row["subject_id"]), row)
    subject_amounts: dict[int, int] = {}
    if command.items:
        seen_groups: set[int] = set()
        for item in command.items:
            if item.group_id in seen_groups:
                raise BillingError("A billing group can appear only once.")
            seen_groups.add(item.group_id)
            row = enrollment_by_group.get(item.group_id)
            if not row:
                raise BillingError("Every billing item must use an active student group.")
            subject_id = int(row["subject_id"])
            subject_amounts[subject_id] = subject_amounts.get(subject_id, 0) + item.amount_minor
    else:
        for price in command.subject_prices:
            if price.subject_id in subject_amounts:
                raise BillingError("A subject price can appear only once.")
            subject_amounts[price.subject_id] = price.amount_minor
    active_subject_ids = set(enrollment_by_subject)
    if command.pricing_mode is BillingPricingMode.PER_SUBJECT:
        missing_subject_ids = active_subject_ids - subject_amounts.keys()
        extra_subject_ids = subject_amounts.keys() - active_subject_ids
        if missing_subject_ids or extra_subject_ids:
            raise BillingError(
                "Enter one amount for every active subject.",
                code="billing_subject_pricing_required",
                status_code=409,
            )
    else:
        subject_amounts = {}
    current_profile = billing_profile_repository.get_billing_profile_row(
        conn,
        command.student_id,
        for_update=True,
    )
    is_first_configuration = current_profile is None
    if current_profile and (
        command.expected_version is None
        or int(current_profile["version"]) != command.expected_version
    ):
        raise BillingError(
            "The billing profile changed. Reload and try again.",
            code="billing_profile_version_conflict",
            status_code=409,
        )
    if current_profile:
        persisted_prices = {
            int(row["subject_id"]): int(row["amount_minor"])
            for row in billing_profile_repository.list_subject_price_rows(
                conn,
                int(current_profile["id"]),
            )
        }
        is_same_configuration = (
            int(current_profile["billing_day"]) == command.billing_day
            and str(current_profile["status"]) == command.status.value
            and str(current_profile["pricing_mode"]) == command.pricing_mode.value
            and (
                int(current_profile["total_amount_minor"])
                if current_profile["total_amount_minor"] is not None
                else None
            )
            == command.total_amount_minor
            and persisted_prices == subject_amounts
        )
        if is_same_configuration:
            if (
                command.status is BillingProfileStatus.ACTIVE
                and command.apply_to is BillingScheduleApplyTo.CURRENT_CYCLE
            ):
                billing_cycles.ensure_current_cycle_invoice(
                    conn,
                    profile=current_profile,
                    now=now,
                )
            unchanged = get_billing_profile(
                conn,
                student_id=command.student_id,
                scope=scope,
            )
            if unchanged is None:
                raise BillingError("Billing profile could not be loaded.")
            return unchanged
    school_today = now.astimezone(SCHOOL_TIMEZONE).date()
    profile_starts_on = (
        current_profile["starts_on"] if current_profile else (command.starts_on or school_today)
    )
    price_effective_on = command.starts_on or school_today
    if current_profile and command.apply_to is BillingScheduleApplyTo.NEXT_CYCLE:
        current_period = billing_cycles.next_billing_period(
            now=now,
            billing_day=command.billing_day,
            starts_on=profile_starts_on,
        )
        price_effective_on = (current_period.replace(day=28) + timedelta(days=4)).replace(day=1)
    normalized_items = [
        (
            int(enrollment_by_subject[subject_id]["group_id"]),
            subject_id,
            str(enrollment_by_subject[subject_id]["subject_name"]),
            amount_minor,
        )
        for subject_id, amount_minor in sorted(subject_amounts.items())
    ]
    profile_id = billing_profile_repository.upsert_billing_profile(
        conn,
        student_id=command.student_id,
        school_id=int(student["school_id"]),
        billing_parent_id=repository.find_billing_parent_id(conn, command.student_id),
        billing_day=command.billing_day,
        starts_on=profile_starts_on,
        status=command.status,
        pricing_mode=command.pricing_mode.value,
        total_amount_minor=command.total_amount_minor,
        expected_version=command.expected_version,
        staff_id=actor.staff_id,
    )
    if not profile_id:
        raise BillingError(
            "The billing profile changed. Reload and try again.",
            code="billing_profile_version_conflict",
            status_code=409,
        )
    try:
        billing_profile_repository.replace_billing_items(
            conn,
            profile_id=profile_id,
            starts_on=price_effective_on,
            items=normalized_items,
            staff_id=actor.staff_id,
        )
        billing_profile_repository.replace_subject_prices(
            conn,
            profile_id=profile_id,
            starts_on=price_effective_on,
            prices=sorted(subject_amounts.items()),
            staff_id=actor.staff_id,
        )
    except (CheckViolation, UniqueViolation) as exc:
        raise BillingError(
            "The billing schedule conflicts with an existing version. Reload and try again.",
            code="billing_profile_conflict",
            status_code=409,
        ) from exc
    repository.insert_audit_event(
        conn,
        event_type="finance.billing_profile_configured",
        entity_type="student_billing_profile",
        entity_id=profile_id,
        detail={
            "student_id": command.student_id,
            "billing_day": command.billing_day,
            "status": command.status.value,
            "pricing_mode": command.pricing_mode.value,
            "total_amount_minor": command.total_amount_minor,
            "subject_ids": sorted(subject_amounts),
            "apply_to": command.apply_to.value,
        },
        staff_id=actor.staff_id,
        account_id=actor.account_id,
    )
    persisted_profile = billing_profile_repository.get_billing_profile_row(
        conn,
        command.student_id,
    )
    if command.status is BillingProfileStatus.ACTIVE and persisted_profile is not None:
        billing_cycles.apply_billing_profile_change(
            conn,
            profile=persisted_profile,
            apply_to=command.apply_to,
            actor=actor,
            is_first_configuration=is_first_configuration,
            now=now,
        )
    profile = get_billing_profile(conn, student_id=command.student_id, scope=scope)
    if profile is None:
        raise BillingError("Billing profile could not be loaded.")
    if (
        profile.status is BillingProfileStatus.ACTIVE
        and command.apply_to is BillingScheduleApplyTo.NEXT_CYCLE
    ):
        _enqueue_invoice_generation_check(
            conn,
            profile_id=profile.profile_id,
            profile_version=profile.version,
        )
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
