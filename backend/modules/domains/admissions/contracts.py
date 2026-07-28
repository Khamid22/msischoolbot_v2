"""Typed, transaction-aware public interface for the admissions domain."""

from __future__ import annotations

import hashlib
import secrets
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

from backend.core.unit_of_work import Connection
from backend.modules.domains.academics.contracts import (
    ActivateAdmissionEnrollmentsCommand,
    activate_admission_enrollments,
)
from backend.modules.domains.admissions import policies, repository
from backend.modules.domains.admissions.domain_types import (
    AdmissionStatus,
    ContractStatus,
    InvoiceKind,
    InvoiceStatus,
    ManualPaymentMethod,
    PaymentSource,
    PaymentStatus,
)
from backend.modules.domains.admissions.schemas import (
    AddPaidInvoiceCommand,
    AdmissionAuditEvent,
    AdmissionContract,
    AdmissionDetail,
    AdmissionGroup,
    AdmissionGroupOption,
    AdmissionLink,
    AdmissionPage,
    AdmissionSummary,
    CancelAdmissionCommand,
    ContractUploadMetadata,
    CreateAdmissionCommand,
    Invoice,
    InvoiceLine,
    InvoicePayment,
    InvoiceQueueItem,
    InvoiceQueuePage,
    ManualPaymentCommand,
    PrivateDocumentReference,
    PublicAdmission,
    ReverseManualPaymentCommand,
    ReviewContractCommand,
    UpdateAdmissionCommand,
    VoidInvoiceCommand,
)
from backend.modules.domains.parent_relationships.contracts import (
    EnsureAdmissionParentCommand,
    ensure_admission_parent,
)
from backend.modules.domains.student_records.contracts import (
    CreateAdmissionStudentCommand,
    create_admission_student,
)
from backend.modules.jobs.contracts import enqueue_on_connection
from backend.modules.jobs.schemas import EnqueueJobCommand

AdmissionError = policies.AdmissionError


@dataclass(frozen=True)
class AdmissionActor:
    staff_id: int | None
    account_id: int | None


@dataclass(frozen=True)
class AdmissionSchoolScope:
    school_ids: frozenset[int]
    all_schools: bool

    def allows(self, school_id: int) -> bool:
        return self.all_schools or school_id in self.school_ids


@dataclass(frozen=True)
class ActivationResult:
    admission_id: int
    student_id: int
    parent_id: int
    student_code: str
    parent_was_reused: bool
    was_already_active: bool = False


@dataclass(frozen=True)
class ManualPaymentResult:
    payment_id: int
    admission_id: int
    activation: ActivationResult | None


def _value(row: Mapping[str, Any], key: str, default: Any = None) -> Any:
    value = row.get(key, default)
    return default if value is None else value


def _contract(row: Mapping[str, Any] | None) -> AdmissionContract | None:
    if not row:
        return None
    return AdmissionContract(
        contract_id=int(row["id"]),
        version=int(row["version"]),
        status=ContractStatus(str(row["status"])),
        original_file_name=str(_value(row, "original_file_name", "")),
        original_mime_type=str(_value(row, "original_mime_type", "")),
        original_size_bytes=int(_value(row, "original_size_bytes", 0)),
        signed_file_name=str(_value(row, "signed_file_name", "")),
        signed_mime_type=str(_value(row, "signed_mime_type", "")),
        signed_size_bytes=row.get("signed_size_bytes"),
        submitted_at=row.get("submitted_at"),
        reviewed_at=row.get("reviewed_at"),
        rejection_reason=str(_value(row, "rejection_reason", "")),
    )


def _invoice(conn: Connection, row: Mapping[str, Any]) -> Invoice:
    invoice_id = int(row["id"])
    lines = [
        InvoiceLine(
            line_id=int(line["id"]),
            group_id=line.get("group_id"),
            subject_id=line.get("subject_id"),
            description=str(line["description"]),
            amount_minor=int(line["amount_minor"]),
        )
        for line in repository.list_invoice_line_rows(conn, invoice_id)
    ]
    payments = [
        InvoicePayment(
            payment_id=int(payment["id"]),
            source=PaymentSource(str(payment["source"])),
            method=str(payment["method"]),
            amount_minor=int(payment["amount_minor"]),
            currency=str(payment["currency"]),
            status=PaymentStatus(str(payment["status"])),
            reference=str(_value(payment, "reference", "")),
            reason=str(_value(payment, "reason", "")),
            paid_at=payment["paid_at"],
        )
        for payment in repository.list_invoice_payment_rows(conn, invoice_id)
    ]
    total_minor = int(row["total_minor"])
    paid_minor = int(row["paid_minor"])
    return Invoice(
        invoice_id=invoice_id,
        invoice_number=str(row["invoice_number"]),
        invoice_kind=InvoiceKind(str(row["invoice_kind"])),
        billing_period=row["billing_period"],
        currency=str(row["currency"]),
        total_minor=total_minor,
        paid_minor=paid_minor,
        balance_minor=max(0, total_minor - paid_minor),
        status=InvoiceStatus(str(row["status"])),
        due_date=row["due_date"],
        issued_at=row.get("issued_at"),
        paid_at=row.get("paid_at"),
        version=int(row["version"]),
        lines=lines,
        payments=payments,
    )


def _detail(conn: Connection, row: Mapping[str, Any]) -> AdmissionDetail:
    admission_id = int(row["id"])
    groups = [
        AdmissionGroup(
            group_id=int(group["group_id"]),
            group_name=str(group["group_name"]),
            subject_id=int(group["subject_id"]),
            subject_name=str(group["subject_name"]),
            monthly_amount_minor=int(group["monthly_amount_minor"]),
        )
        for group in repository.list_admission_group_rows(conn, admission_id)
    ]
    contract_row = repository.get_current_contract_row(conn, admission_id)
    invoice_rows = repository.list_invoice_rows(conn, admission_id)
    audit_rows = repository.list_admission_audit_rows(conn, admission_id)
    return AdmissionDetail(
        admission_id=admission_id,
        school_id=int(row["school_id"]),
        school_name=str(row["school_name"]),
        student_full_name=str(row["student_full_name"]),
        student_phone=str(_value(row, "student_phone", "")),
        parent_full_name=str(row["parent_full_name"]),
        parent_phone=str(row["parent_phone"]),
        parent_telegram_username=str(_value(row, "parent_telegram_username", "")),
        preferred_language=str(row["preferred_language"]),
        service_start_date=row.get("service_start_date"),
        first_due_date=row["first_due_date"],
        billing_day=int(row["billing_day"]),
        currency=str(row["currency"]),
        status=AdmissionStatus(str(row["status"])),
        version=int(row["version"]),
        activated_student_id=row.get("activated_student_id"),
        activated_parent_id=row.get("activated_parent_id"),
        activated_at=row.get("activated_at"),
        cancellation_reason=str(_value(row, "cancellation_reason", "")),
        groups=groups,
        contract=_contract(contract_row),
        invoices=[_invoice(conn, invoice_row) for invoice_row in invoice_rows],
        audit_events=[
            AdmissionAuditEvent(
                event_id=int(event["id"]),
                event_type=str(event["event_type"]),
                entity_type=str(event["entity_type"]),
                entity_id=int(event["entity_id"]),
                detail_summary=", ".join(
                    f"{key}: {value}"
                    for key, value in sorted(
                        dict(event.get("detail_json") or {}).items()
                    )
                ),
                actor_staff_id=event.get("actor_staff_id"),
                created_at=event["created_at"],
            )
            for event in audit_rows
        ],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _get_public_admission_row(conn: Connection, token_hash: str) -> Mapping[str, Any]:
    access_state = repository.touch_admission_access_token(
        conn,
        token_hash,
        request_limit=policies.ADMISSION_TOKEN_RATE_LIMIT,
        window_seconds=policies.ADMISSION_TOKEN_RATE_WINDOW_SECONDS,
    )
    if access_state == "rate_limited":
        raise policies.AdmissionError(
            "Too many admission link requests. Please try again shortly.",
            code="admission_link_rate_limited",
            status_code=429,
        )
    row = repository.get_admission_by_token_hash(conn, token_hash)
    if not row:
        raise policies.AdmissionError(
            "This admission link is invalid or expired.",
            code="admission_link_invalid",
            status_code=404,
        )
    return row


def list_group_options(
    conn: Connection,
    scope: AdmissionSchoolScope,
) -> list[AdmissionGroupOption]:
    return [
        AdmissionGroupOption(
            group_id=int(row["group_id"]),
            school_id=int(row["school_id"]),
            school_name=str(row["school_name"]),
            group_name=str(row["group_name"]),
            subject_id=int(row["subject_id"]),
            subject_name=str(row["subject_name"]),
        )
        for row in repository.list_group_option_rows(
            conn,
            school_ids=scope.school_ids,
            all_schools=scope.all_schools,
        )
    ]


def create_admission(
    conn: Connection,
    command: CreateAdmissionCommand,
    *,
    actor: AdmissionActor,
    scope: AdmissionSchoolScope,
) -> int:
    if not scope.allows(command.school_id):
        raise policies.AdmissionError(
            "The selected school is outside your assigned scope.",
            code="school_scope_denied",
            status_code=403,
        )
    group_ids = [group.group_id for group in command.groups]
    if len(group_ids) != len(set(group_ids)):
        raise policies.AdmissionError("Each group may be selected only once.")
    rows = repository.lock_group_selection_rows(
        conn,
        school_id=command.school_id,
        group_ids=group_ids,
    )
    if len(rows) != len(group_ids):
        raise policies.AdmissionError("One or more selected groups are unavailable.")
    subject_ids = [int(row["subject_id"]) for row in rows]
    if len(subject_ids) != len(set(subject_ids)):
        raise policies.AdmissionError("Select only one group for each subject.")
    admission_id = repository.insert_admission(
        conn,
        school_id=command.school_id,
        student_full_name=" ".join(command.student_full_name.strip().split()),
        student_phone=command.student_phone.strip(),
        parent_full_name=" ".join(command.parent_full_name.strip().split()),
        parent_phone=command.parent_phone.strip(),
        parent_telegram_username=command.parent_telegram_username.strip().lstrip("@"),
        preferred_language=command.preferred_language,
        service_start_date=command.service_start_date,
        first_due_date=command.first_due_date,
        billing_day=command.billing_day,
        created_by_staff_id=actor.staff_id,
    )
    repository.insert_group_selections(
        conn,
        admission_id=admission_id,
        group_rows=rows,
        amount_by_group_id={
            group.group_id: group.monthly_amount_minor for group in command.groups
        },
    )
    repository.insert_audit_event(
        conn,
        event_type="admission_created",
        entity_type="admission",
        entity_id=admission_id,
        detail={"school_id": command.school_id, "group_ids": group_ids},
        staff_id=actor.staff_id,
        account_id=actor.account_id,
    )
    return admission_id


def issue_access_link(
    conn: Connection,
    admission_id: int,
    *,
    actor: AdmissionActor,
    scope: AdmissionSchoolScope,
    expires_in_days: int = 14,
    replace_active: bool = True,
) -> AdmissionLink:
    get_admission(conn, admission_id, scope=scope, for_update=True)
    access_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(access_token.encode("utf-8")).hexdigest()
    expires_at = datetime.now(UTC) + timedelta(days=max(1, min(expires_in_days, 30)))
    repository.insert_access_token(
        conn,
        admission_id=admission_id,
        token_hash=token_hash,
        expires_at=expires_at,
        replace_active=replace_active,
    )
    repository.insert_audit_event(
        conn,
        event_type="admission_link_issued",
        entity_type="admission",
        entity_id=admission_id,
        detail={"expires_at": expires_at.isoformat(), "replaced": replace_active},
        staff_id=actor.staff_id,
        account_id=actor.account_id,
    )
    return AdmissionLink(access_token=access_token, expires_at=expires_at)


def list_admissions(
    conn: Connection,
    *,
    scope: AdmissionSchoolScope,
    query: str,
    status: str,
    limit: int,
) -> AdmissionPage:
    rows = repository.list_admission_rows(
        conn,
        school_ids=scope.school_ids,
        all_schools=scope.all_schools,
        query=query.strip(),
        status=status,
        limit=max(1, min(limit, 100)),
    )
    items = [
        AdmissionSummary(
            admission_id=int(row["admission_id"]),
            school_id=int(row["school_id"]),
            school_name=str(row["school_name"]),
            student_full_name=str(row["student_full_name"]),
            parent_full_name=str(row["parent_full_name"]),
            parent_phone=str(row["parent_phone"]),
            status=AdmissionStatus(str(row["status"])),
            contract_status=(
                ContractStatus(str(row["contract_status"]))
                if row.get("contract_status")
                else None
            ),
            first_invoice_status=(
                InvoiceStatus(str(row["first_invoice_status"]))
                if row.get("first_invoice_status")
                else None
            ),
            first_due_date=row["first_due_date"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]
    total = int(rows[0]["total_count"]) if rows else 0
    return AdmissionPage(items=items, total=total)


def update_admission(
    conn: Connection,
    admission_id: int,
    command: UpdateAdmissionCommand,
    *,
    actor: AdmissionActor,
    scope: AdmissionSchoolScope,
) -> None:
    get_admission(conn, admission_id, scope=scope, for_update=True)
    if not repository.update_admission(
        conn,
        admission_id=admission_id,
        expected_version=command.expected_version,
        student_full_name=" ".join(command.student_full_name.strip().split()),
        student_phone=command.student_phone.strip(),
        parent_full_name=" ".join(command.parent_full_name.strip().split()),
        parent_phone=command.parent_phone.strip(),
        parent_telegram_username=command.parent_telegram_username.strip().lstrip("@"),
        preferred_language=command.preferred_language,
        service_start_date=command.service_start_date,
        first_due_date=command.first_due_date,
        billing_day=command.billing_day,
    ):
        raise policies.AdmissionError(
            "The admission changed or can no longer be edited.",
            code="admission_version_conflict",
            status_code=409,
        )
    repository.insert_audit_event(
        conn,
        event_type="admission_updated",
        entity_type="admission",
        entity_id=admission_id,
        detail={"version": command.expected_version},
        staff_id=actor.staff_id,
        account_id=actor.account_id,
    )


def list_invoices(
    conn: Connection,
    *,
    scope: AdmissionSchoolScope,
    query: str,
    status: str,
    limit: int,
) -> InvoiceQueuePage:
    rows = repository.list_scoped_invoice_rows(
        conn,
        school_ids=scope.school_ids,
        all_schools=scope.all_schools,
        query=query.strip(),
        status=status,
        limit=max(1, min(limit, 100)),
    )
    items = [
        InvoiceQueueItem(
            invoice_id=int(row["id"]),
            invoice_number=str(row["invoice_number"]),
            admission_id=int(row["admission_id"]),
            school_id=int(row["school_id"]),
            school_name=str(row["school_name"]),
            student_full_name=str(row["student_full_name"]),
            parent_full_name=str(row["parent_full_name"]),
            parent_phone=str(row["parent_phone"]),
            invoice_kind=InvoiceKind(str(row["invoice_kind"])),
            currency=str(row["currency"]),
            total_minor=int(row["total_minor"]),
            paid_minor=int(row["paid_minor"]),
            balance_minor=int(row["total_minor"]) - int(row["paid_minor"]),
            status=InvoiceStatus(str(row["status"])),
            due_date=row["due_date"],
            issued_at=row.get("issued_at"),
            paid_at=row.get("paid_at"),
            version=int(row["version"]),
        )
        for row in rows
    ]
    return InvoiceQueuePage(
        items=items,
        total=int(rows[0]["total_count"]) if rows else 0,
    )


def get_admission(
    conn: Connection,
    admission_id: int,
    *,
    scope: AdmissionSchoolScope,
    for_update: bool = False,
) -> AdmissionDetail:
    row = repository.get_admission_row(conn, admission_id, for_update=for_update)
    if not row:
        raise policies.AdmissionError(
            "Admission not found.",
            code="admission_not_found",
            status_code=404,
        )
    if not scope.allows(int(row["school_id"])):
        raise policies.AdmissionError(
            "Admission not found.",
            code="admission_not_found",
            status_code=404,
        )
    return _detail(conn, row)


def add_contract(
    conn: Connection,
    admission_id: int,
    metadata: ContractUploadMetadata,
    *,
    actor: AdmissionActor,
    scope: AdmissionSchoolScope,
) -> int:
    detail = get_admission(conn, admission_id, scope=scope, for_update=True)
    policies.ensure_contract_can_be_sent(detail.status)
    contract_id = repository.insert_contract(
        conn,
        admission_id=admission_id,
        object_key=metadata.object_key,
        original_file_name=metadata.original_file_name,
        mime_type=metadata.mime_type,
        size_bytes=metadata.size_bytes,
    )
    repository.insert_audit_event(
        conn,
        event_type="admission_contract_uploaded",
        entity_type="admission_contract",
        entity_id=contract_id,
        detail={"admission_id": admission_id, "versioned": True},
        staff_id=actor.staff_id,
        account_id=actor.account_id,
    )
    return contract_id


def send_contract(
    conn: Connection,
    admission_id: int,
    *,
    actor: AdmissionActor,
    scope: AdmissionSchoolScope,
) -> None:
    detail = get_admission(conn, admission_id, scope=scope, for_update=True)
    policies.ensure_contract_can_be_sent(detail.status)
    contract_row = repository.get_current_contract_row(conn, admission_id, for_update=True)
    if not contract_row:
        raise policies.AdmissionError("Upload a contract before sending it.")
    repository.mark_contract_sent(
        conn,
        admission_id=admission_id,
        contract_id=int(contract_row["id"]),
    )
    repository.insert_audit_event(
        conn,
        event_type="admission_contract_sent",
        entity_type="admission_contract",
        entity_id=int(contract_row["id"]),
        detail={"admission_id": admission_id},
        staff_id=actor.staff_id,
        account_id=actor.account_id,
    )


def submit_contract(
    conn: Connection,
    token_hash: str,
    metadata: ContractUploadMetadata,
) -> int:
    admission_row = _get_public_admission_row(conn, token_hash)
    contract_row = repository.get_current_contract_row(
        conn,
        int(admission_row["id"]),
        for_update=True,
    )
    if not contract_row:
        raise policies.AdmissionError("The contract is not available.")
    policies.ensure_contract_can_be_submitted(
        ContractStatus(str(contract_row["status"]))
    )
    submitted_contract_id = repository.submit_signed_contract(
        conn,
        contract_id=int(contract_row["id"]),
        object_key=metadata.object_key,
        original_file_name=metadata.original_file_name,
        mime_type=metadata.mime_type,
        size_bytes=metadata.size_bytes,
    )
    if submitted_contract_id <= 0:
        raise policies.AdmissionError("The signed contract could not be saved.")
    repository.insert_audit_event(
        conn,
        event_type="admission_contract_submitted",
        entity_type="admission_contract",
        entity_id=submitted_contract_id,
        detail={
            "admission_id": int(admission_row["id"]),
            "versioned_resubmission": submitted_contract_id != int(contract_row["id"]),
        },
        staff_id=None,
        account_id=None,
    )
    return int(admission_row["id"])


def review_contract(
    conn: Connection,
    admission_id: int,
    *,
    accepted: bool,
    reason: str,
    actor: AdmissionActor,
    scope: AdmissionSchoolScope,
) -> None:
    get_admission(conn, admission_id, scope=scope, for_update=True)
    contract_row = repository.get_current_contract_row(conn, admission_id, for_update=True)
    if not contract_row:
        raise policies.AdmissionError("The contract is not available.")
    policies.ensure_contract_can_be_reviewed(
        ContractStatus(str(contract_row["status"]))
    )
    if not accepted and len(reason.strip()) < 2:
        raise policies.AdmissionError("A rejection reason is required.")
    repository.review_contract(
        conn,
        admission_id=admission_id,
        contract_id=int(contract_row["id"]),
        accepted=accepted,
        staff_id=actor.staff_id,
        reason=reason.strip(),
    )
    repository.insert_audit_event(
        conn,
        event_type=(
            "admission_contract_accepted"
            if accepted
            else "admission_contract_rejected"
        ),
        entity_type="admission_contract",
        entity_id=int(contract_row["id"]),
        detail={"admission_id": admission_id, "reason": reason.strip()},
        staff_id=actor.staff_id,
        account_id=actor.account_id,
    )


def issue_invoice(
    conn: Connection,
    admission_id: int,
    *,
    due_date: date,
    billing_period: date,
    invoice_kind: InvoiceKind,
    actor: AdmissionActor,
    scope: AdmissionSchoolScope | None = None,
) -> int:
    row = repository.get_admission_row(conn, admission_id, for_update=True)
    if not row:
        raise policies.AdmissionError("Admission not found.", status_code=404)
    if scope and not scope.allows(int(row["school_id"])):
        raise policies.AdmissionError("Admission not found.", status_code=404)
    contract_row = repository.get_current_contract_row(conn, admission_id, for_update=True)
    policies.ensure_invoice_can_be_issued(
        AdmissionStatus(str(row["status"])),
        ContractStatus(str(contract_row["status"])) if contract_row else None,
    )
    existing = repository.find_invoice_for_period(
        conn,
        admission_id=admission_id,
        billing_period=billing_period,
        invoice_kind=invoice_kind.value,
    )
    if existing:
        return int(existing["id"])
    group_rows = repository.list_admission_group_rows(conn, admission_id)
    total_minor = sum(int(group["monthly_amount_minor"]) for group in group_rows)
    if total_minor <= 0:
        raise policies.AdmissionError("The admission does not have billable groups.")
    invoice_id = repository.insert_invoice(
        conn,
        admission_id=admission_id,
        invoice_number=repository.next_invoice_number(conn),
        invoice_kind=invoice_kind.value,
        billing_period=billing_period,
        total_minor=total_minor,
        due_date=due_date,
        created_by_staff_id=actor.staff_id,
    )
    repository.insert_invoice_lines_from_admission(
        conn,
        admission_id=admission_id,
        invoice_id=invoice_id,
    )
    repository.insert_audit_event(
        conn,
        event_type="admission_invoice_issued",
        entity_type="invoice",
        entity_id=invoice_id,
        detail={
            "admission_id": admission_id,
            "invoice_kind": invoice_kind.value,
            "total_minor": total_minor,
        },
        staff_id=actor.staff_id,
        account_id=actor.account_id,
    )
    return invoice_id


def activate_paid_admission(
    conn: Connection,
    admission_id: int,
    *,
    actor: AdmissionActor,
) -> ActivationResult:
    admission_row = repository.get_admission_row(conn, admission_id, for_update=True)
    if not admission_row:
        raise policies.AdmissionError("Admission not found.", status_code=404)
    if str(admission_row["status"]) == AdmissionStatus.ACTIVE.value:
        return ActivationResult(
            admission_id=admission_id,
            student_id=int(admission_row["activated_student_id"]),
            parent_id=int(admission_row["activated_parent_id"]),
            student_code="",
            parent_was_reused=True,
            was_already_active=True,
        )
    contract_row = repository.get_current_contract_row(conn, admission_id, for_update=True)
    first_invoice_row = repository.get_first_invoice_row(conn, admission_id, for_update=True)
    if not contract_row or str(contract_row["status"]) != ContractStatus.ACCEPTED.value:
        raise policies.AdmissionError("An accepted contract is required for activation.")
    if not first_invoice_row or str(first_invoice_row["status"]) != InvoiceStatus.PAID.value:
        raise policies.AdmissionError("The first invoice must be paid before activation.")
    group_rows = repository.list_admission_group_rows(conn, admission_id)
    group_ids = tuple(int(group["group_id"]) for group in group_rows)
    locked_groups = repository.lock_group_selection_rows(
        conn,
        school_id=int(admission_row["school_id"]),
        group_ids=group_ids,
    )
    if len(locked_groups) != len(group_ids):
        raise policies.AdmissionError(
            "A selected group is no longer available. Customer Support must review the admission."
        )
    student = create_admission_student(
        conn,
        CreateAdmissionStudentCommand(
            full_name=str(admission_row["student_full_name"]),
            school_id=int(admission_row["school_id"]),
        ),
    )
    activate_admission_enrollments(
        conn,
        ActivateAdmissionEnrollmentsCommand(
            student_id=student.student_id,
            group_ids=group_ids,
        ),
    )
    parent = ensure_admission_parent(
        conn,
        EnsureAdmissionParentCommand(
            student_id=student.student_id,
            full_name=str(admission_row["parent_full_name"]),
            phone=str(admission_row["parent_phone"]),
            telegram_username=str(
                _value(admission_row, "parent_telegram_username", "")
            ),
            preferred_language=str(admission_row["preferred_language"]),
        ),
    )
    repository.link_invoice_to_people(
        conn,
        admission_id=admission_id,
        student_id=student.student_id,
        parent_id=parent.parent_id,
    )
    repository.activate_admission(
        conn,
        admission_id=admission_id,
        student_id=student.student_id,
        parent_id=parent.parent_id,
    )
    repository.insert_audit_event(
        conn,
        event_type="admission_activated",
        entity_type="admission",
        entity_id=admission_id,
        detail={
            "student_id": student.student_id,
            "parent_id": parent.parent_id,
            "parent_was_reused": parent.was_reused,
            "group_ids": list(group_ids),
        },
        staff_id=actor.staff_id,
        account_id=actor.account_id,
    )
    enqueue_on_connection(
        conn,
        EnqueueJobCommand(
            topic="admissions.activation_completed",
            payload={
                "admission_id": admission_id,
                "student_id": student.student_id,
                "parent_id": parent.parent_id,
            },
            idempotency_key=f"admission-activation:{admission_id}",
            max_attempts=5,
        ),
    )
    return ActivationResult(
        admission_id=admission_id,
        student_id=student.student_id,
        parent_id=parent.parent_id,
        student_code=student.student_code,
        parent_was_reused=parent.was_reused,
    )


def record_manual_payment(
    conn: Connection,
    invoice_id: int,
    *,
    amount_minor: int,
    method: str,
    paid_at: datetime,
    reference: str,
    reason: str,
    expected_version: int,
    actor: AdmissionActor,
    scope: AdmissionSchoolScope,
) -> ManualPaymentResult:
    invoice_row = repository.get_invoice_row(conn, invoice_id, for_update=True)
    if not invoice_row:
        raise policies.AdmissionError("Invoice not found.", status_code=404)
    admission_id = int(invoice_row["admission_id"])
    admission_row = repository.get_admission_row(conn, admission_id, for_update=True)
    if not admission_row or not scope.allows(int(admission_row["school_id"])):
        raise policies.AdmissionError("Invoice not found.", status_code=404)
    if int(invoice_row["version"]) != expected_version:
        raise policies.AdmissionError(
            "The invoice changed. Refresh before recording the payment.",
            code="invoice_version_conflict",
            status_code=409,
        )
    policies.ensure_invoice_can_accept_payment(
        InvoiceStatus(str(invoice_row["status"]))
    )
    if repository.has_pending_payme_transaction(conn, invoice_id):
        raise policies.AdmissionError(
            "A Payme transaction is pending for this invoice.",
            code="payme_transaction_pending",
            status_code=409,
        )
    balance_minor = int(invoice_row["total_minor"]) - int(invoice_row["paid_minor"])
    if amount_minor > balance_minor:
        raise policies.AdmissionError("Payment exceeds the invoice balance.")
    payment_id = repository.insert_manual_payment(
        conn,
        invoice_id=invoice_id,
        amount_minor=amount_minor,
        method=method,
        paid_at=paid_at,
        reference=reference.strip(),
        reason=reason.strip(),
        staff_id=actor.staff_id,
    )
    new_paid_minor = int(invoice_row["paid_minor"]) + amount_minor
    invoice_status = policies.invoice_status_for_balance(
        total_minor=int(invoice_row["total_minor"]),
        paid_minor=new_paid_minor,
    )
    if not repository.update_invoice_paid_amount(
        conn,
        invoice_id=invoice_id,
        expected_version=expected_version,
        paid_minor=new_paid_minor,
        status=invoice_status.value,
    ):
        raise policies.AdmissionError(
            "The invoice changed. Refresh before recording the payment.",
            code="invoice_version_conflict",
            status_code=409,
        )
    repository.insert_audit_event(
        conn,
        event_type="manual_invoice_payment_recorded",
        entity_type="invoice_payment",
        entity_id=payment_id,
        detail={
            "invoice_id": invoice_id,
            "admission_id": admission_id,
            "amount_minor": amount_minor,
            "method": method,
            "reference": reference.strip(),
            "reason": reason.strip(),
        },
        staff_id=actor.staff_id,
        account_id=actor.account_id,
    )
    activation = None
    if (
        invoice_status is InvoiceStatus.PAID
        and str(invoice_row["invoice_kind"]) == InvoiceKind.FIRST.value
    ):
        activation = activate_paid_admission(conn, admission_id, actor=actor)
    return ManualPaymentResult(
        payment_id=payment_id,
        admission_id=admission_id,
        activation=activation,
    )


def reverse_manual_payment(
    conn: Connection,
    payment_id: int,
    *,
    expected_invoice_version: int,
    reason: str,
    actor: AdmissionActor,
    scope: AdmissionSchoolScope,
) -> int:
    payment_row = repository.get_invoice_payment_row(
        conn,
        payment_id,
        for_update=True,
    )
    if not payment_row:
        raise policies.AdmissionError("Payment not found.", status_code=404)
    invoice_row = repository.get_invoice_row(
        conn,
        int(payment_row["invoice_id"]),
        for_update=True,
    )
    admission_id = int(invoice_row["admission_id"])
    admission_row = repository.get_admission_row(conn, admission_id, for_update=True)
    if not admission_row or not scope.allows(int(admission_row["school_id"])):
        raise policies.AdmissionError("Payment not found.", status_code=404)
    if int(invoice_row["version"]) != expected_invoice_version:
        raise policies.AdmissionError(
            "The invoice changed. Refresh before reversing the payment.",
            code="invoice_version_conflict",
            status_code=409,
        )
    if not repository.reverse_manual_payment(
        conn,
        payment_id=payment_id,
        staff_id=actor.staff_id,
        reason=reason.strip(),
    ):
        raise policies.AdmissionError(
            "Only a completed manual payment can be reversed.",
            code="payment_cannot_be_reversed",
            status_code=409,
        )
    new_paid_minor = max(
        0,
        int(invoice_row["paid_minor"]) - int(payment_row["amount_minor"]),
    )
    new_status = policies.invoice_status_for_balance(
        total_minor=int(invoice_row["total_minor"]),
        paid_minor=new_paid_minor,
    )
    if not repository.update_invoice_paid_amount(
        conn,
        invoice_id=int(invoice_row["id"]),
        expected_version=expected_invoice_version,
        paid_minor=new_paid_minor,
        status=new_status.value,
    ):
        raise policies.AdmissionError(
            "The invoice changed. Refresh before reversing the payment.",
            code="invoice_version_conflict",
            status_code=409,
        )
    repository.set_admission_payment_review(conn, admission_id=admission_id)
    repository.insert_audit_event(
        conn,
        event_type="manual_invoice_payment_reversed",
        entity_type="invoice_payment",
        entity_id=payment_id,
        detail={
            "invoice_id": int(invoice_row["id"]),
            "admission_id": admission_id,
            "reason": reason.strip(),
        },
        staff_id=actor.staff_id,
        account_id=actor.account_id,
    )
    return admission_id


def void_invoice(
    conn: Connection,
    invoice_id: int,
    *,
    expected_version: int,
    reason: str,
    actor: AdmissionActor,
    scope: AdmissionSchoolScope,
) -> int:
    invoice_row = repository.get_invoice_row(conn, invoice_id, for_update=True)
    if not invoice_row:
        raise policies.AdmissionError("Invoice not found.", status_code=404)
    admission_id = int(invoice_row["admission_id"])
    admission_row = repository.get_admission_row(conn, admission_id, for_update=True)
    if not admission_row or not scope.allows(int(admission_row["school_id"])):
        raise policies.AdmissionError("Invoice not found.", status_code=404)
    if repository.has_pending_payme_transaction(conn, invoice_id):
        raise policies.AdmissionError(
            "Cancel the pending Payme transaction before voiding the invoice.",
            code="payme_transaction_pending",
            status_code=409,
        )
    if not repository.void_invoice(
        conn,
        invoice_id=invoice_id,
        expected_version=expected_version,
        reason=reason.strip(),
    ):
        raise policies.AdmissionError(
            "Only an unpaid invoice can be voided.",
            code="invoice_cannot_be_voided",
            status_code=409,
        )
    repository.insert_audit_event(
        conn,
        event_type="admission_invoice_voided",
        entity_type="invoice",
        entity_id=invoice_id,
        detail={"admission_id": admission_id, "reason": reason.strip()},
        staff_id=actor.staff_id,
        account_id=actor.account_id,
    )
    return admission_id


def cancel_admission(
    conn: Connection,
    admission_id: int,
    *,
    expected_version: int,
    reason: str,
    actor: AdmissionActor,
    scope: AdmissionSchoolScope,
) -> None:
    get_admission(conn, admission_id, scope=scope, for_update=True)
    if not repository.cancel_admission(
        conn,
        admission_id=admission_id,
        expected_version=expected_version,
        reason=reason.strip(),
    ):
        raise policies.AdmissionError(
            "The admission changed or can no longer be cancelled.",
            code="admission_version_conflict",
            status_code=409,
        )
    repository.insert_audit_event(
        conn,
        event_type="admission_cancelled",
        entity_type="admission",
        entity_id=admission_id,
        detail={"reason": reason.strip()},
        staff_id=actor.staff_id,
        account_id=actor.account_id,
    )


def get_public_admission(
    conn: Connection,
    token_hash: str,
    *,
    payme_is_available: bool,
    checkout_url: str,
    merchant_id: str,
    callback_url: str,
) -> PublicAdmission:
    row = _get_public_admission_row(conn, token_hash)
    admission_id = int(row["id"])
    contract_row = repository.get_current_contract_row(conn, admission_id)
    invoice_row = repository.get_first_invoice_row(conn, admission_id)
    return PublicAdmission(
        admission_id=admission_id,
        student_full_name=str(row["student_full_name"]),
        school_name=str(row["school_name"]),
        preferred_language=str(row["preferred_language"]),
        status=AdmissionStatus(str(row["status"])),
        contract=_contract(contract_row),
        invoice=_invoice(conn, invoice_row) if invoice_row else None,
        payme_is_available=payme_is_available,
        checkout_url=checkout_url,
        merchant_id=merchant_id,
        callback_url=callback_url,
    )


def get_staff_contract_document(
    conn: Connection,
    admission_id: int,
    *,
    signed: bool,
    scope: AdmissionSchoolScope,
) -> PrivateDocumentReference:
    get_admission(conn, admission_id, scope=scope)
    row = repository.get_current_contract_row(conn, admission_id)
    if not row:
        raise policies.AdmissionError("The contract is not available.", status_code=404)
    object_key = str(
        _value(row, "signed_object_key" if signed else "original_object_key", "")
    )
    file_name = str(
        _value(row, "signed_file_name" if signed else "original_file_name", "")
    )
    if not object_key:
        raise policies.AdmissionError("The contract document is not available.", status_code=404)
    return PrivateDocumentReference(
        object_key=object_key,
        original_file_name=file_name,
    )


def get_public_contract_document(
    conn: Connection,
    token_hash: str,
) -> PrivateDocumentReference:
    admission_row = _get_public_admission_row(conn, token_hash)
    row = repository.get_current_contract_row(conn, int(admission_row["id"]))
    if not row or not str(_value(row, "original_object_key", "")):
        raise policies.AdmissionError("The contract is not available.", status_code=404)
    return PrivateDocumentReference(
        object_key=str(row["original_object_key"]),
        original_file_name=str(row["original_file_name"]),
    )


__all__ = [
    "ActivationResult",
    "AddPaidInvoiceCommand",
    "AdmissionActor",
    "AdmissionAuditEvent",
    "AdmissionContract",
    "AdmissionDetail",
    "AdmissionError",
    "AdmissionGroup",
    "AdmissionGroupOption",
    "AdmissionLink",
    "AdmissionPage",
    "AdmissionSchoolScope",
    "AdmissionStatus",
    "AdmissionSummary",
    "CancelAdmissionCommand",
    "ContractStatus",
    "ContractUploadMetadata",
    "CreateAdmissionCommand",
    "Invoice",
    "InvoiceKind",
    "InvoiceLine",
    "InvoicePayment",
    "InvoiceQueueItem",
    "InvoiceQueuePage",
    "InvoiceStatus",
    "ManualPaymentCommand",
    "ManualPaymentMethod",
    "ManualPaymentResult",
    "PrivateDocumentReference",
    "PublicAdmission",
    "ReverseManualPaymentCommand",
    "ReviewContractCommand",
    "UpdateAdmissionCommand",
    "VoidInvoiceCommand",
    "add_contract",
    "activate_paid_admission",
    "cancel_admission",
    "create_admission",
    "get_admission",
    "get_public_contract_document",
    "get_public_admission",
    "get_staff_contract_document",
    "issue_access_link",
    "issue_invoice",
    "list_admissions",
    "list_group_options",
    "list_invoices",
    "record_manual_payment",
    "reverse_manual_payment",
    "review_contract",
    "send_contract",
    "submit_contract",
    "update_admission",
    "void_invoice",
]
