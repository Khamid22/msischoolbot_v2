"""Business rules for the Customer Support records workspace."""

from __future__ import annotations

import base64
import json
import math
import secrets
import string
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from backend.core.database import connect_auth_db
from backend.modules.domains.finance.contracts import (
    find_migrated_invoice_id,
    list_compatibility_payment_records,
)
from backend.modules.domains.identity.contracts import (
    ProvisionStudentAccountCommand,
    provision_student_account,
    reset_student_password,
)
from backend.modules.domains.organization import contracts as organization_contract
from backend.modules.domains.parent_relationships.contracts import (
    CreateParentInviteCommand,
)
from backend.modules.domains.parent_relationships.contracts import (
    create_parent_invite as create_parent_invite_contract,
)
from backend.modules.domains.support_cases import (
    customer_records_repository_contracts as repository,
)


class CustomerSupportError(ValueError):
    status_code = 400
    code = "customer_support_error"
    details: Any = None

    def __init__(self, message: str, *, details: Any = None):
        super().__init__(message)
        self.details = details


class NotFoundError(CustomerSupportError):
    status_code = 404
    code = "record_not_found"


class ScopeError(CustomerSupportError):
    status_code = 403
    code = "school_scope_denied"


class VersionConflictError(CustomerSupportError):
    status_code = 409
    code = "version_conflict"


class MigratedPaymentError(CustomerSupportError):
    status_code = 409
    code = "payment_uses_invoice_ledger"


class DependencyConflictError(CustomerSupportError):
    status_code = 409
    code = "active_dependencies"


class DuplicateLinkError(CustomerSupportError):
    status_code = 409
    code = "duplicate_parent_student_link"


@dataclass(frozen=True)
class SupportActor:
    staff_id: int | None
    account_id: int | None
    login: str


@dataclass(frozen=True)
class SchoolScope:
    all_schools: bool
    school_ids: tuple[int, ...]
    schools: tuple[dict[str, Any], ...]
    raw: str


def _connect():
    return connect_auth_db()


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _optional_text(value: Any) -> str:
    return str(value or "").strip()


def _row_dict(row: Any) -> dict[str, Any]:
    return dict(row) if row else {}


def _json_value(value: Any) -> Any:
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_value(item) for item in value]
    return value


def _public_row(row: Any) -> dict[str, Any]:
    return _json_value(_row_dict(row))


def _scope_tokens(raw: str) -> set[str]:
    normalized = str(raw or "").replace(";", ",").replace("|", ",")
    return {token.strip().casefold() for token in normalized.split(",") if token.strip()}


def load_scope(conn, actor: SupportActor) -> SchoolScope:
    staff = repository.get_staff_scope_row(
        conn, staff_id=actor.staff_id, account_id=actor.account_id
    )
    if not staff:
        raise ScopeError("Customer Support staff scope could not be resolved.")
    raw = str(staff["school_scope"] or "").strip() if staff else ""
    tokens = _scope_tokens(raw)
    schools = [_public_row(row) for row in repository.list_school_rows(conn)]
    all_schools = not tokens or bool(tokens & {"*", "all", "all schools"})
    if all_schools:
        allowed = schools
    else:
        allowed = [
            school
            for school in schools
            if str(school.get("school_key") or "").casefold() in tokens
            or str(school.get("school_name") or "").casefold() in tokens
            or str(school.get("id") or "") in tokens
        ]
    return SchoolScope(
        all_schools=all_schools,
        school_ids=tuple(int(school["id"]) for school in allowed),
        schools=tuple(allowed),
        raw=raw,
    )


def _ensure_school(scope: SchoolScope, school_id: Any) -> int:
    try:
        parsed = int(school_id)
    except (TypeError, ValueError) as exc:
        raise CustomerSupportError("School is required.") from exc
    if parsed <= 0 or (not scope.all_schools and parsed not in scope.school_ids):
        raise ScopeError("This school is outside your Customer Support scope.")
    return parsed


def _ensure_student_visible(conn, scope: SchoolScope, student_id: int):
    row = repository.get_student_row(conn, int(student_id))
    if not row:
        raise NotFoundError("Student was not found.")
    school_id = int(row["school_id"] or 0)
    if not scope.all_schools and school_id not in scope.school_ids:
        raise ScopeError("This student is outside your Customer Support scope.")
    return row


def _ensure_parent_visible(conn, scope: SchoolScope, parent_id: int):
    row = repository.get_parent_row(conn, int(parent_id))
    if not row:
        raise NotFoundError("Parent was not found.")
    if not scope.all_schools:
        visible = repository.list_parent_student_rows(
            conn,
            parent_id=int(parent_id),
            allowed_school_ids=list(scope.school_ids),
            all_schools=False,
        )
        if not visible:
            raise ScopeError("This parent has no students in your Customer Support scope.")
    return row


def _ensure_version(current: Any, expected: Any):
    try:
        current_version = int(current)
        expected_version = int(expected)
    except (TypeError, ValueError) as exc:
        raise CustomerSupportError("A valid expectedVersion is required.") from exc
    if current_version != expected_version:
        raise VersionConflictError(
            "This record changed after you opened it. Reload and try again.",
            details={"currentVersion": current_version},
        )
    return expected_version


def _encode_cursor(item: dict[str, Any]) -> str:
    raw = json.dumps(
        {
            "name": _text(item.get("display_name")).casefold(),
            "kind": _text(item.get("kind")).casefold(),
            "id": max(0, int(item.get("id") or 0)),
        },
        separators=(",", ":"),
    )
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii").rstrip("=")


def _decode_cursor(value: str) -> tuple[str, str, int]:
    token = str(value or "").strip()
    if not token:
        return "", "", 0
    try:
        padded = token + "=" * (-len(token) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
        name = _text(payload.get("name")).casefold()
        kind = _text(payload.get("kind")).casefold()
        record_id = max(0, int(payload.get("id") or 0))
        if not name or kind not in {"student", "parent"} or record_id <= 0:
            raise ValueError("invalid cursor fields")
        return name, kind, record_id
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise CustomerSupportError("The records cursor is invalid.") from exc


def _temporary_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits
    while True:
        value = "".join(secrets.choice(alphabet) for _ in range(max(10, length)))
        if any(char.islower() for char in value) and any(char.isupper() for char in value) and any(char.isdigit() for char in value):
            return value


def _next_student_code(conn, prefix: str) -> str:
    normalized = _text(prefix).upper() or "MSI"
    maximum = 0
    for row in repository.list_student_codes(conn, normalized):
        code = str(row["student_code"] or "").strip().upper()
        suffix = code[len(normalized) :] if code.startswith(normalized) else ""
        if suffix.isdigit():
            maximum = max(maximum, int(suffix))
    return f"{normalized}{maximum + 1:05d}"


def _audit(
    conn,
    actor: SupportActor,
    *,
    event_type: str,
    entity_type: str,
    entity_id: int,
    before: Any = None,
    after: Any = None,
    reason: str = "",
    scope: SchoolScope | None = None,
):
    detail = {
        "actor_login": actor.login,
        "before": _json_value(before or {}),
        "after": _json_value(after or {}),
    }
    if reason:
        detail["reason"] = reason
    if scope is not None:
        detail["school_scope"] = "all" if scope.all_schools else list(scope.school_ids)
    repository.insert_audit_event(
        conn,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=int(entity_id),
        detail=detail,
        actor_staff_id=actor.staff_id,
        actor_account_id=actor.account_id,
    )


def context(actor: SupportActor):
    with _connect() as conn:
        scope = load_scope(conn, actor)
    return {
        "schools": list(scope.schools),
        "allSchools": scope.all_schools,
        "recordTypes": ["all", "student", "parent"],
        "statuses": ["all", "active", "disabled", "archived"],
        "languages": ["uz", "ru", "en"],
        "permissions": {
            "manageStudents": True,
            "manageParents": True,
            "managePayments": True,
            "manageAcademicPlacement": False,
        },
    }


def search_records(
    actor: SupportActor,
    *,
    query: str = "",
    kind: str = "all",
    status: str = "all",
    school_id: int | None = None,
    exclude_parent_id: int | None = None,
    cursor: str = "",
    limit: int = 25,
):
    normalized_kind = _text(kind).casefold() or "all"
    if normalized_kind not in {"all", "student", "parent"}:
        raise CustomerSupportError("Unsupported record type filter.")
    normalized_status = _text(status).casefold() or "all"
    if normalized_status not in {"all", "active", "disabled", "archived"}:
        raise CustomerSupportError("Unsupported status filter.")
    normalized_limit = max(1, min(int(limit or 25), 50))
    cursor_name, cursor_kind, cursor_id = _decode_cursor(cursor)
    with _connect() as conn:
        scope = load_scope(conn, actor)
        selected_school = _ensure_school(scope, school_id) if school_id else None
        excluded_parent = None
        if exclude_parent_id:
            excluded_parent = int(_ensure_parent_visible(conn, scope, exclude_parent_id)["id"])
        rows = repository.search_record_rows(
            conn,
            query=_text(query),
            kind=normalized_kind,
            status=normalized_status,
            school_id=selected_school,
            exclude_parent_id=excluded_parent,
            allowed_school_ids=list(scope.school_ids),
            all_schools=scope.all_schools,
            cursor_name=cursor_name,
            cursor_kind=cursor_kind,
            cursor_id=cursor_id,
            limit=normalized_limit + 1,
        )
    has_more = len(rows) > normalized_limit
    items = [_public_row(row) for row in rows[:normalized_limit]]
    return {
        "items": items,
        "nextCursor": _encode_cursor(items[-1]) if has_more and items else None,
        "hasMore": has_more,
    }


def _payment_state(payment: dict[str, Any]) -> str:
    if payment.get("voided_at") or str(payment.get("status") or "").casefold() == "voided":
        return "voided"
    if payment.get("paid_at") or str(payment.get("status") or "").casefold() == "paid":
        return "paid"
    due = payment.get("due_date")
    if isinstance(due, str):
        due = organization_contract.parse_date(due)
    if not due:
        return "due"
    if due < date.today():
        return "debt"
    if due > date.today():
        return "upcoming"
    return "due"


def _payments_payload(rows: list[Any]):
    payments = []
    totals = {"paid": 0.0, "due": 0.0, "debt": 0.0, "upcoming": 0.0}
    currency = "UZS"
    for raw in rows:
        payment = _public_row(raw)
        payment["state"] = _payment_state(payment)
        currency = str(payment.get("currency") or currency)
        state = payment["state"]
        if state in totals:
            totals[state] += float(payment.get("amount") or 0)
        payments.append(payment)
    return {"items": payments, "totals": totals, "currency": currency}


def _canonical_payment_rows(conn, student: Any) -> list[dict[str, Any]]:
    legacy_student_row_id = int(student["legacy_student_row_id"] or 0)
    if legacy_student_row_id <= 0:
        return []
    rows = list_compatibility_payment_records(
        conn,
        student_id=int(student["id"]),
        student_row_id=legacy_student_row_id,
    )
    return [
        {
            "id": row.payment_id,
            "student_id": row.student_id,
            "group_id": None,
            "subject_id": None,
            "subject": row.subject,
            "month_label": row.month_label,
            "amount": row.amount,
            "currency": row.currency,
            "status": row.status,
            "due_date": row.due_date,
            "paid_at": row.paid_at,
            "notes": row.notes,
            "version": row.version,
            "voided_at": row.voided_at,
            "void_reason": row.void_reason,
            "created_by_staff_id": row.created_by_staff_id,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }
        for row in rows
    ]


def _activity(rows: list[Any]):
    return [
        {
            "id": int(row["id"]),
            "eventType": str(row["event_type"]),
            "entityType": str(row["entity_type"]),
            "actor": str(row["actor"] or "System"),
            "details": _json_value(row["detail_json"] or {}),
            "createdAt": _json_value(row["created_at"]),
        }
        for row in rows
    ]


def _student_detail(conn, scope: SchoolScope, student_id: int):
    student = _ensure_student_visible(conn, scope, student_id)
    enrollments = [_public_row(row) for row in repository.list_student_enrollment_rows(conn, student_id)]
    for enrollment in enrollments:
        present = int(enrollment.get("present_count") or 0)
        absent = int(enrollment.get("absent_count") or 0)
        justified = int(enrollment.get("justified_count") or 0)
        total = present + absent + justified
        enrollment["attendanceRate"] = round(((present + justified) / total) * 100) if total else 0
    parents = [_public_row(row) for row in repository.list_student_parent_rows(conn, student_id)]
    parent_invites = [
        _public_row(row)
        for row in repository.list_student_parent_invite_rows(conn, student_id)
    ]
    payments = _payments_payload(_canonical_payment_rows(conn, student))
    activity = _activity(repository.list_audit_rows(
        conn, entity_types=["student", "student_account"], entity_id=student_id
    ))
    return {
        "kind": "student",
        "profile": _public_row(student),
        "academic": enrollments,
        "parents": parents,
        "parentInvites": parent_invites,
        "payments": payments,
        "activity": activity,
    }


def student_detail(actor: SupportActor, student_id: int):
    with _connect() as conn:
        return _student_detail(conn, load_scope(conn, actor), int(student_id))


def _parent_detail(conn, scope: SchoolScope, parent_id: int):
    parent = _ensure_parent_visible(conn, scope, parent_id)
    children = repository.list_parent_student_rows(
        conn,
        parent_id=parent_id,
        allowed_school_ids=list(scope.school_ids),
        all_schools=scope.all_schools,
    )
    activity = _activity(repository.list_audit_rows(
        conn, entity_types=["parent", "parent_account"], entity_id=parent_id
    ))
    return {
        "kind": "parent",
        "profile": _public_row(parent),
        "children": [_public_row(row) for row in children],
        "hiddenChildCount": repository.count_parent_hidden_links(
            conn,
            parent_id=parent_id,
            allowed_school_ids=list(scope.school_ids),
            all_schools=scope.all_schools,
        ),
        "activity": activity,
    }


def parent_detail(actor: SupportActor, parent_id: int):
    with _connect() as conn:
        return _parent_detail(conn, load_scope(conn, actor), int(parent_id))


def create_student(actor: SupportActor, payload: dict[str, Any]):
    full_name = _text(payload.get("fullName"))
    if len(full_name) < 2:
        raise CustomerSupportError("Student full name is required.")
    phone = _optional_text(payload.get("phone"))
    photo_url = _optional_text(payload.get("photoUrl"))
    description = _optional_text(payload.get("profileDescription"))
    temporary_password = _temporary_password()
    with _connect() as conn:
        scope = load_scope(conn, actor)
        school_id = _ensure_school(scope, payload.get("schoolId"))
        school = repository.get_school_row(conn, school_id)
        if not school or str(school["status"] or "") != "active":
            raise CustomerSupportError("Selected school is unavailable.")
        prefix = organization_contract.student_code_prefix(str(school["school_key"] or ""))
        repository.acquire_student_identifier_advisory_lock(conn)
        student_code = _next_student_code(conn, prefix)
        legacy_id = repository.next_legacy_student_id(conn)
        student_id = repository.insert_student(
            conn,
            student_code=student_code,
            full_name=full_name,
            school_id=school_id,
            phone=phone,
            photo_url=photo_url,
            profile_description=description,
            legacy_student_row_id=legacy_id,
        )
        if student_id <= 0:
            raise CustomerSupportError("Unable to create the student.")
        account = provision_student_account(
            conn,
            ProvisionStudentAccountCommand(
                student_id=student_id,
                login=student_code,
                initial_password=temporary_password,
                full_name=full_name,
                school_id=school_id,
            ),
        )
        if account.account_id <= 0:
            raise CustomerSupportError("Unable to provision the student account.")
        repository.update_student_account_phone(conn, student_id=student_id, phone=phone)
        after = repository.get_student_row(conn, student_id)
        _audit(
            conn,
            actor,
            event_type="customer_support.student_created",
            entity_type="student",
            entity_id=student_id,
            after=_public_row(after),
            scope=scope,
        )
        conn.commit()
        detail = _student_detail(conn, scope, student_id)
    return {
        "record": detail,
        "credentials": {
            "login": student_code,
            "temporaryPassword": temporary_password,
            "mustChangePassword": True,
        },
    }


def update_student(actor: SupportActor, student_id: int, payload: dict[str, Any]):
    with _connect() as conn:
        scope = load_scope(conn, actor)
        current = _ensure_student_visible(conn, scope, student_id)
        expected = _ensure_version(current["version"], payload.get("expectedVersion"))
        school_id = _ensure_school(scope, payload.get("schoolId", current["school_id"]))
        if school_id != int(current["school_id"] or 0):
            school = repository.get_school_row(conn, school_id)
            if not school or str(school["status"] or "") != "active":
                raise CustomerSupportError("Selected school is unavailable.")
            blockers = [_public_row(row) for row in repository.list_active_enrollment_blockers(conn, student_id)]
            if blockers:
                raise DependencyConflictError(
                    "The school cannot change while the student has active group enrollments.",
                    details={"groups": blockers},
                )
        full_name = _text(payload.get("fullName", current["full_name"]))
        if len(full_name) < 2:
            raise CustomerSupportError("Student full name is required.")
        status = _text(payload.get("status", current["status"])).casefold()
        if status not in {"active", "disabled"}:
            raise CustomerSupportError("Use the archive action to archive a student.")
        updated = repository.update_student_record(
            conn,
            student_id=student_id,
            expected_version=expected,
            full_name=full_name,
            school_id=school_id,
            phone=_optional_text(payload.get("phone", current["phone"])),
            photo_url=_optional_text(payload.get("photoUrl", current["photo_url"])),
            profile_description=_optional_text(payload.get("profileDescription", current["profile_description"])),
            status=status,
        )
        if not updated:
            raise VersionConflictError("This student changed. Reload and try again.")
        after = repository.get_student_row(conn, student_id)
        _audit(
            conn,
            actor,
            event_type="customer_support.student_updated",
            entity_type="student",
            entity_id=student_id,
            before=_public_row(current),
            after=_public_row(after),
            reason=_optional_text(payload.get("reason")),
            scope=scope,
        )
        conn.commit()
        return _student_detail(conn, scope, student_id)


def set_student_lifecycle(
    actor: SupportActor, student_id: int, *, expected_version: int, active: bool, reason: str
):
    normalized_reason = _text(reason)
    if not normalized_reason:
        raise CustomerSupportError("A reason is required.")
    with _connect() as conn:
        scope = load_scope(conn, actor)
        current = _ensure_student_visible(conn, scope, student_id)
        expected = _ensure_version(current["version"], expected_version)
        target = "active" if active else "archived"
        if not active:
            blockers = [_public_row(row) for row in repository.list_active_enrollment_blockers(conn, student_id)]
            if blockers:
                raise DependencyConflictError(
                    "Academic Department must remove the student from active groups before archiving.",
                    details={"groups": blockers},
                )
        updated = repository.set_student_lifecycle(
            conn, student_id=student_id, expected_version=expected, status=target
        )
        if not updated:
            raise VersionConflictError("This student changed. Reload and try again.")
        after = repository.get_student_row(conn, student_id)
        _audit(
            conn,
            actor,
            event_type=f"customer_support.student_{'reactivated' if active else 'archived'}",
            entity_type="student",
            entity_id=student_id,
            before=_public_row(current),
            after=_public_row(after),
            reason=normalized_reason,
            scope=scope,
        )
        conn.commit()
        return _student_detail(conn, scope, student_id)


def reset_student_access(actor: SupportActor, student_id: int, *, expected_version: int):
    password = _temporary_password()
    with _connect() as conn:
        scope = load_scope(conn, actor)
        student = _ensure_student_visible(conn, scope, student_id)
        expected = _ensure_version(student["version"], expected_version)
        legacy_id = int(student["legacy_student_row_id"] or 0)
        outcome = reset_student_password(
            legacy_id,
            password,
            actor_account_id=actor.account_id,
            conn=conn,
        )
        if not outcome.changed:
            raise CustomerSupportError(outcome.message or "Unable to reset student access.")
        if not repository.bump_student_version(
            conn, student_id=student_id, expected_version=expected
        ):
            raise VersionConflictError("This student changed. Reload and try again.")
        _audit(
            conn,
            actor,
            event_type="customer_support.student_access_reset",
            entity_type="student",
            entity_id=student_id,
            before={
                "accountStatus": student["account_status"],
                "mustChangePassword": bool(student["must_change_password"]),
            },
            after={"sessionVersion": outcome.session_version, "mustChangePassword": True},
            scope=scope,
        )
        conn.commit()
        record = _student_detail(conn, scope, student_id)
    return {
        "record": record,
        "credentials": {
            "login": str(student["login"] or student["student_code"]),
            "temporaryPassword": password,
            "mustChangePassword": True,
        },
    }


def update_parent(actor: SupportActor, parent_id: int, payload: dict[str, Any]):
    with _connect() as conn:
        scope = load_scope(conn, actor)
        current = _ensure_parent_visible(conn, scope, parent_id)
        expected = _ensure_version(current["version"], payload.get("expectedVersion"))
        display_name = _text(payload.get("displayName", current["display_name"]))
        if len(display_name) < 2:
            raise CustomerSupportError("Parent name is required.")
        status = _text(payload.get("status", current["status"])).casefold()
        if status not in {"active", "disabled"}:
            raise CustomerSupportError("Parent status must be active or disabled.")
        language = _text(payload.get("preferredLanguage", current["preferred_language"])).casefold()
        if language not in {"uz", "ru", "en"}:
            raise CustomerSupportError("Preferred language must be Uzbek, Russian, or English.")
        updated = repository.update_parent_record(
            conn,
            parent_id=parent_id,
            expected_version=expected,
            display_name=display_name,
            phone=_optional_text(payload.get("phone", current["phone"])),
            telegram_username=_optional_text(payload.get("telegramUsername", current["telegram_username"])).lstrip("@"),
            preferred_language=language,
            status=status,
        )
        if not updated:
            raise VersionConflictError("This parent changed. Reload and try again.")
        after = repository.get_parent_row(conn, parent_id)
        _audit(
            conn,
            actor,
            event_type="customer_support.parent_updated",
            entity_type="parent",
            entity_id=parent_id,
            before=_public_row(current),
            after=_public_row(after),
            reason=_optional_text(payload.get("reason")),
            scope=scope,
        )
        conn.commit()
        return _parent_detail(conn, scope, parent_id)


def set_parent_lifecycle(
    actor: SupportActor, parent_id: int, *, expected_version: int, active: bool, reason: str
):
    normalized_reason = _text(reason)
    if not normalized_reason:
        raise CustomerSupportError("A reason is required.")
    with _connect() as conn:
        scope = load_scope(conn, actor)
        current = _ensure_parent_visible(conn, scope, parent_id)
        expected = _ensure_version(current["version"], expected_version)
        target = "active" if active else "disabled"
        updated = repository.update_parent_record(
            conn,
            parent_id=parent_id,
            expected_version=expected,
            display_name=str(current["display_name"] or ""),
            phone=str(current["phone"] or ""),
            telegram_username=str(current["telegram_username"] or ""),
            preferred_language=str(current["preferred_language"] or "ru"),
            status=target,
        )
        if not updated:
            raise VersionConflictError("This parent changed. Reload and try again.")
        after = repository.get_parent_row(conn, parent_id)
        _audit(
            conn,
            actor,
            event_type=f"customer_support.parent_{'reactivated' if active else 'deactivated'}",
            entity_type="parent",
            entity_id=parent_id,
            before=_public_row(current),
            after=_public_row(after),
            reason=normalized_reason,
            scope=scope,
        )
        conn.commit()
        return _parent_detail(conn, scope, parent_id)


def link_parent_child(
    actor: SupportActor,
    parent_id: int,
    student_id: int,
    *,
    expected_version: int,
):
    with _connect() as conn:
        scope = load_scope(conn, actor)
        parent = _ensure_parent_visible(conn, scope, parent_id)
        expected = _ensure_version(parent["version"], expected_version)
        student = _ensure_student_visible(conn, scope, student_id)
        if not repository.insert_parent_student_link(
            conn, parent_id=parent_id, student_id=student_id
        ):
            raise DuplicateLinkError("This student is already linked to this parent.")
        if not repository.bump_parent_version(
            conn, parent_id=parent_id, expected_version=expected
        ):
            raise VersionConflictError("This parent changed. Reload and try again.")
        _audit(
            conn,
            actor,
            event_type="customer_support.parent_child_linked",
            entity_type="parent",
            entity_id=parent_id,
            after={"studentId": student_id, "studentName": student["full_name"]},
            scope=scope,
        )
        conn.commit()
        return _parent_detail(conn, scope, parent_id)


def unlink_parent_child(
    actor: SupportActor,
    parent_id: int,
    student_id: int,
    reason: str,
    *,
    expected_version: int,
):
    normalized_reason = _text(reason)
    if not normalized_reason:
        raise CustomerSupportError("A reason is required to unlink a child.")
    with _connect() as conn:
        scope = load_scope(conn, actor)
        parent = _ensure_parent_visible(conn, scope, parent_id)
        expected = _ensure_version(parent["version"], expected_version)
        student = _ensure_student_visible(conn, scope, student_id)
        if not repository.remove_parent_student_link(conn, parent_id=parent_id, student_id=student_id):
            raise NotFoundError("Parent-child link was not found.")
        if not repository.bump_parent_version(
            conn, parent_id=parent_id, expected_version=expected
        ):
            raise VersionConflictError("This parent changed. Reload and try again.")
        _audit(
            conn,
            actor,
            event_type="customer_support.parent_child_unlinked",
            entity_type="parent",
            entity_id=parent_id,
            before={"studentId": student_id, "studentName": student["full_name"]},
            reason=normalized_reason,
            scope=scope,
        )
        conn.commit()
        return _parent_detail(conn, scope, parent_id)


def create_parent_invite(
    actor: SupportActor, student_id: int, *, expected_version: int
):
    with _connect() as conn:
        scope = load_scope(conn, actor)
        student = _ensure_student_visible(conn, scope, student_id)
        _ensure_version(student["version"], expected_version)
        legacy_id = int(student["legacy_student_row_id"] or 0)
        invite = create_parent_invite_contract(
            conn,
            CreateParentInviteCommand(
                legacy_student_row_id=legacy_id,
                issued_by_staff_id=actor.staff_id,
                replace_pending=True,
            ),
        )
        _audit(
            conn,
            actor,
            event_type="customer_support.parent_invite_created",
            entity_type="student",
            entity_id=student_id,
            after={"inviteCreated": True},
            scope=scope,
        )
        conn.commit()
    return {"inviteCode": invite.invite_code, "studentId": student_id}


def list_student_payments(actor: SupportActor, student_id: int):
    with _connect() as conn:
        scope = load_scope(conn, actor)
        student = _ensure_student_visible(conn, scope, student_id)
        return _payments_payload(_canonical_payment_rows(conn, student))


def _positive_amount(value: Any) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise CustomerSupportError("Payment amount must be a number.") from exc
    if not math.isfinite(parsed) or parsed <= 0:
        raise CustomerSupportError("Payment amount must be greater than zero.")
    return round(parsed, 2)


def _date_value(value: Any, label: str, *, timestamp: bool = False) -> str:
    raw = _optional_text(value)
    if not raw:
        return ""
    parsed = organization_contract.parse_date(raw)
    if not parsed:
        raise CustomerSupportError(f"{label} is not a valid date.")
    if timestamp:
        return datetime.combine(parsed, datetime.min.time(), tzinfo=UTC).isoformat()
    return parsed.isoformat()


def create_payment(actor: SupportActor, student_id: int, payload: dict[str, Any]):
    amount = _positive_amount(payload.get("amount"))
    try:
        subject_id = int(payload.get("subjectId") or 0)
    except (TypeError, ValueError) as exc:
        raise CustomerSupportError("Subject is required.") from exc
    currency = _text(payload.get("currency") or "UZS").upper()
    if len(currency) != 3:
        raise CustomerSupportError("Currency must use a three-letter code.")
    due_date = _date_value(payload.get("dueDate"), "Due date")
    paid_at = _date_value(payload.get("paidAt"), "Paid date", timestamp=True)
    with _connect() as conn:
        scope = load_scope(conn, actor)
        student = _ensure_student_visible(conn, scope, student_id)
        _ensure_version(student["version"], payload.get("expectedVersion"))
        group = repository.find_active_group_for_subject(
            conn, student_id=student_id, subject_id=subject_id
        )
        if not group:
            raise CustomerSupportError("The student is not actively enrolled in this subject.")
        payment_id = repository.insert_payment(
            conn,
            student_id=student_id,
            group_id=int(group["group_id"]),
            month_label=_optional_text(payload.get("monthLabel")),
            amount=amount,
            currency=currency,
            due_date=due_date,
            paid_at=paid_at,
            notes=_optional_text(payload.get("notes")),
            actor_staff_id=actor.staff_id,
        )
        payment = repository.get_payment_row(conn, payment_id)
        _audit(
            conn,
            actor,
            event_type="customer_support.payment_created",
            entity_type="payment",
            entity_id=payment_id,
            after=_public_row(payment),
            scope=scope,
        )
        _audit(
            conn,
            actor,
            event_type="customer_support.student_payment_created",
            entity_type="student",
            entity_id=student_id,
            after={"paymentId": payment_id, "amount": amount, "currency": currency},
            scope=scope,
        )
        conn.commit()
        return _payments_payload(repository.list_payment_rows(conn, student_id=student_id))


def _payment_context(conn, actor: SupportActor, payment_id: int):
    scope = load_scope(conn, actor)
    payment = repository.get_payment_row(conn, payment_id)
    if not payment:
        raise NotFoundError("Payment was not found.")
    migrated_invoice_id = find_migrated_invoice_id(
        conn,
        legacy_payment_id=payment_id,
    )
    if migrated_invoice_id is not None:
        raise MigratedPaymentError(
            "This payment is managed in the invoice ledger. "
            "Use a reversal or invoice void instead."
        )
    _ensure_student_visible(conn, scope, int(payment["student_id"]))
    return scope, payment


def update_payment(actor: SupportActor, payment_id: int, payload: dict[str, Any]):
    with _connect() as conn:
        scope, current = _payment_context(conn, actor, payment_id)
        if current["voided_at"]:
            raise CustomerSupportError("A voided payment cannot be edited.")
        expected = _ensure_version(current["version"], payload.get("expectedVersion"))
        currency = _text(payload.get("currency", current["currency"])).upper()
        if len(currency) != 3:
            raise CustomerSupportError("Currency must use a three-letter code.")
        updated = repository.update_payment_record(
            conn,
            payment_id=payment_id,
            expected_version=expected,
            month_label=_optional_text(payload.get("monthLabel", current["month_label"])),
            amount=_positive_amount(payload.get("amount", current["amount"])),
            currency=currency,
            due_date=_date_value(payload.get("dueDate", current["due_date"]), "Due date"),
            notes=_optional_text(payload.get("notes", current["notes"])),
        )
        if not updated:
            raise VersionConflictError("This payment changed. Reload and try again.")
        after = repository.get_payment_row(conn, payment_id)
        _audit(
            conn,
            actor,
            event_type="customer_support.payment_updated",
            entity_type="payment",
            entity_id=payment_id,
            before=_public_row(current),
            after=_public_row(after),
            reason=_optional_text(payload.get("reason")),
            scope=scope,
        )
        _audit(
            conn,
            actor,
            event_type="customer_support.student_payment_updated",
            entity_type="student",
            entity_id=int(current["student_id"]),
            before={"paymentId": payment_id, "version": current["version"]},
            after={"paymentId": payment_id, "version": after["version"]},
            reason=_optional_text(payload.get("reason")),
            scope=scope,
        )
        conn.commit()
        return _payments_payload(repository.list_payment_rows(conn, student_id=int(current["student_id"])))


def settle_payment(actor: SupportActor, payment_id: int, payload: dict[str, Any]):
    with _connect() as conn:
        scope, current = _payment_context(conn, actor, payment_id)
        if current["voided_at"]:
            raise CustomerSupportError("A voided payment cannot change settlement status.")
        expected = _ensure_version(current["version"], payload.get("expectedVersion"))
        paid = bool(payload.get("paid"))
        paid_at = _date_value(payload.get("paidAt"), "Paid date", timestamp=True) if paid else ""
        updated = repository.settle_payment(
            conn,
            payment_id=payment_id,
            expected_version=expected,
            paid=paid,
            paid_at=paid_at,
        )
        if not updated:
            raise VersionConflictError("This payment changed. Reload and try again.")
        after = repository.get_payment_row(conn, payment_id)
        _audit(
            conn,
            actor,
            event_type=f"customer_support.payment_{'settled' if paid else 'reopened'}",
            entity_type="payment",
            entity_id=payment_id,
            before=_public_row(current),
            after=_public_row(after),
            reason=_optional_text(payload.get("reason")),
            scope=scope,
        )
        _audit(
            conn,
            actor,
            event_type=f"customer_support.student_payment_{'settled' if paid else 'reopened'}",
            entity_type="student",
            entity_id=int(current["student_id"]),
            before={"paymentId": payment_id, "status": current["status"]},
            after={"paymentId": payment_id, "status": after["status"]},
            reason=_optional_text(payload.get("reason")),
            scope=scope,
        )
        conn.commit()
        return _payments_payload(repository.list_payment_rows(conn, student_id=int(current["student_id"])))


def void_payment(actor: SupportActor, payment_id: int, payload: dict[str, Any]):
    reason = _text(payload.get("reason"))
    if not reason:
        raise CustomerSupportError("A reason is required to void a payment.")
    with _connect() as conn:
        scope, current = _payment_context(conn, actor, payment_id)
        if current["voided_at"]:
            raise CustomerSupportError("This payment is already voided.")
        expected = _ensure_version(current["version"], payload.get("expectedVersion"))
        updated = repository.void_payment(
            conn,
            payment_id=payment_id,
            expected_version=expected,
            reason=reason,
            actor_account_id=actor.account_id,
        )
        if not updated:
            raise VersionConflictError("This payment changed. Reload and try again.")
        after = repository.get_payment_row(conn, payment_id)
        _audit(
            conn,
            actor,
            event_type="customer_support.payment_voided",
            entity_type="payment",
            entity_id=payment_id,
            before=_public_row(current),
            after=_public_row(after),
            reason=reason,
            scope=scope,
        )
        _audit(
            conn,
            actor,
            event_type="customer_support.student_payment_voided",
            entity_type="student",
            entity_id=int(current["student_id"]),
            before={"paymentId": payment_id, "status": current["status"]},
            after={"paymentId": payment_id, "status": "voided"},
            reason=reason,
            scope=scope,
        )
        conn.commit()
        return _payments_payload(repository.list_payment_rows(conn, student_id=int(current["student_id"])))


__all__ = [
    "CustomerSupportError",
    "DependencyConflictError",
    "DuplicateLinkError",
    "NotFoundError",
    "SchoolScope",
    "ScopeError",
    "SupportActor",
    "VersionConflictError",
    "context",
    "create_parent_invite",
    "create_payment",
    "create_student",
    "link_parent_child",
    "list_student_payments",
    "parent_detail",
    "reset_student_access",
    "search_records",
    "set_parent_lifecycle",
    "set_student_lifecycle",
    "settle_payment",
    "student_detail",
    "unlink_parent_child",
    "update_parent",
    "update_payment",
    "update_student",
    "void_payment",
]
