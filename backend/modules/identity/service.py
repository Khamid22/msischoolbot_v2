"""Canonical account authentication, provisioning, and password lifecycle."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, Callable

from backend.modules.identity.passwords import generate_password_hash, verify_password_hash
from backend.modules.organization.canonical import normalize_school_code
from backend.modules.identity import repository
from backend.modules.identity.database import DB_LOCK, connect
from backend.core.access.roles import normalize_role


LOGGER = logging.getLogger("msi.identity")


PASSWORD_LOGIN_ALLOWED_STATUS = "active"
MIN_PASSWORD_LENGTH = 8
ACCOUNT_AUTH_ROLES = {
    "system_admin",
    "ceo",
    "customer_support",
    "student",
    "parent",
    "teacher",
    "academic_director",
    "head_of_department",
    "hr_manager",
}
STAFF_ACCOUNT_ROLES = {
    "system_admin",
    "ceo",
    "customer_support",
    "academic_director",
    "head_of_department",
    "hr_manager",
}


@dataclass(frozen=True)
class PasswordChangeOutcome:
    changed: bool
    message: str = ""
    code: str = ""
    session_version: int = 0


def normalize_login(value: Any) -> str:
    return str(value or "").strip().casefold()


def _text(value: Any) -> str:
    return str(value or "").strip()


def _to_int(value: Any) -> int | None:
    try:
        parsed_value = int(value)
    except (TypeError, ValueError):
        return None
    return parsed_value if parsed_value > 0 else None


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return _text(value).casefold() in {"1", "true", "yes", "on"}


def _row_to_dict(row: Any) -> dict[str, Any] | None:
    if not row:
        return None
    return dict(row)


def _with_connection(conn: Any | None, callback: Callable[[Any], Any]) -> Any:
    if conn is not None:
        return callback(conn)
    with connect() as opened_conn:
        return callback(opened_conn)


def _normalize_account(row: Any) -> dict[str, Any] | None:
    normalized_row = _row_to_dict(row)
    if not normalized_row:
        return None
    account_id = _to_int(normalized_row.get("id"))
    if account_id is None:
        return None
    role = normalize_role(normalized_row.get("role"))
    return {
        "id": account_id,
        "login": _text(normalized_row.get("login")) or None,
        "password_hash": _text(normalized_row.get("password_hash")) or None,
        "role": role,
        "raw_role": _text(normalized_row.get("role")),
        "status": _text(normalized_row.get("status")).casefold() or "disabled",
        "full_name": _text(normalized_row.get("full_name")),
        "phone": _text(normalized_row.get("phone")) or None,
        "legacy_source_table": _text(normalized_row.get("legacy_source_table")),
        "legacy_source_id": _to_int(normalized_row.get("legacy_source_id")),
        "must_change_password": _to_bool(normalized_row.get("must_change_password")),
        "password_changed_at": normalized_row.get("password_changed_at"),
        "last_login_at": normalized_row.get("last_login_at"),
        "session_version": _to_int(normalized_row.get("session_version")) or 1,
    }


def get_account_by_login(login: Any, conn: Any | None = None) -> dict[str, Any] | None:
    normalized_login = normalize_login(login)
    if not normalized_login:
        return None
    return _with_connection(
        conn,
        lambda active_conn: _normalize_account(
            repository.get_account_by_login_row(active_conn, normalized_login)
        ),
    )


def get_account_by_id(account_id: Any, conn: Any | None = None) -> dict[str, Any] | None:
    parsed_account_id = _to_int(account_id)
    if parsed_account_id is None:
        return None
    return _with_connection(
        conn,
        lambda active_conn: _normalize_account(
            repository.get_account_by_id_row(active_conn, parsed_account_id)
        ),
    )


def verify_account_password(account: dict[str, Any] | None, password: Any) -> bool:
    return bool(account and verify_password_hash(account.get("password_hash"), password))


def _student_profile(conn: Any, account_id: int) -> dict[str, Any] | None:
    row = _row_to_dict(repository.get_student_profile_row(conn, account_id))
    if not row:
        return None
    return {
        "role": "student",
        "profile_id": _to_int(row.get("profile_id")),
        "account_id": _to_int(row.get("account_id")),
        "student_id": _to_int(row.get("student_id")),
        "student_db_id": _to_int(row.get("canonical_student_id") or row.get("student_id")),
        "student_legacy_row_id": _to_int(row.get("legacy_student_row_id")),
        "student_code": _text(row.get("current_student_code") or row.get("student_code")),
        "student_enrollment_id": _to_int(row.get("enrollment_id")),
        "full_name": _text(row.get("full_name")),
        "school_code": normalize_school_code(row.get("school_code"), default=""),
        "status": _text(row.get("profile_status")).casefold() or "disabled",
    }


def _parent_profile(conn: Any, account_id: int) -> dict[str, Any] | None:
    row = _row_to_dict(repository.get_parent_profile_row(conn, account_id))
    if not row:
        return None
    return {
        "role": "parent",
        "profile_id": _to_int(row.get("profile_id")),
        "account_id": _to_int(row.get("account_id")),
        "parent_id": _to_int(row.get("parent_id")),
        "full_name": _text(row.get("full_name")),
        "telegram_username": _text(row.get("telegram_username")),
        "telegram_user_id": _to_int(row.get("telegram_user_id")),
        "status": _text(row.get("profile_status")).casefold() or "disabled",
    }


def _staff_profile(conn: Any, account_id: int, role: str) -> dict[str, Any] | None:
    row = _row_to_dict(repository.get_staff_profile_row(conn, account_id))
    if not row:
        return None
    return {
        "role": role,
        "profile_id": _to_int(row.get("profile_id")),
        "account_id": _to_int(row.get("account_id")),
        "staff_id": _to_int(row.get("staff_id")),
        "job_title": _text(row.get("job_title")),
        "department": _text(row.get("department")),
        "staff_login": _text(row.get("staff_login")),
        "legacy_staff_role": _text(row.get("legacy_staff_role")),
        "is_owner": bool(row.get("is_owner")),
        "status": _text(row.get("profile_status")).casefold() or "disabled",
    }


def _teacher_profile(conn: Any, account_id: int) -> dict[str, Any] | None:
    row = _row_to_dict(repository.get_teacher_profile_row(conn, account_id))
    if not row:
        return None
    return {
        "role": "teacher",
        "profile_id": _to_int(row.get("profile_id")),
        "account_id": _to_int(row.get("account_id")),
        "teacher_id": _to_int(row.get("teacher_id")),
        "staff_id": _to_int(row.get("staff_id")),
        "teacher_code": _text(row.get("teacher_code")),
        "full_name": _text(row.get("full_name")),
        "status": _text(row.get("profile_status")).casefold() or "disabled",
    }


def load_account_profile(
    account: dict[str, Any] | None,
    conn: Any | None = None,
) -> dict[str, Any] | None:
    if not account:
        return None
    account_id = _to_int(account.get("id"))
    role = normalize_role(account.get("role"))
    if account_id is None or role not in ACCOUNT_AUTH_ROLES:
        return None

    def _load(active_conn: Any) -> dict[str, Any] | None:
        if role == "student":
            return _student_profile(active_conn, account_id)
        if role == "parent":
            return _parent_profile(active_conn, account_id)
        if role == "teacher":
            return _teacher_profile(active_conn, account_id)
        if role in STAFF_ACCOUNT_ROLES:
            return _staff_profile(active_conn, account_id, role)
        return None

    return _with_connection(conn, _load)


def _profile_allows_login(profile: dict[str, Any] | None) -> bool:
    return bool(
        profile
        and _text(profile.get("status")).casefold() == PASSWORD_LOGIN_ALLOWED_STATUS
    )


def build_session_payload(
    account: dict[str, Any] | None,
    profile: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not account or not profile:
        return None
    account_id = _to_int(account.get("id"))
    role = normalize_role(account.get("role"))
    if account_id is None or role not in ACCOUNT_AUTH_ROLES:
        return None
    if normalize_role(profile.get("role")) != role:
        return None

    auth_login = _text(account.get("login"))
    payload: dict[str, Any] = {
        "account_id": account_id,
        "account_role": role,
        "canonical_role": role,
        "auth_login": auth_login,
        "must_change_password": bool(account.get("must_change_password")),
        "session_version": _to_int(account.get("session_version")) or 1,
    }

    if role == "student":
        student_db_id = _to_int(profile.get("student_db_id"))
        student_code = _text(profile.get("student_code")) or auth_login
        if student_db_id is None or not student_code:
            return None
        payload.update(
            {
                "auth_role": "student",
                "auth_login": student_code,
                "student_db_id": student_db_id,
                "student_id": student_code,
                "student_full_name": _text(profile.get("full_name")),
            }
        )
        enrollment_id = _to_int(profile.get("student_enrollment_id"))
        if enrollment_id is not None:
            payload["student_enrollment_id"] = enrollment_id
        school_code = normalize_school_code(profile.get("school_code"), default="")
        if school_code:
            payload["student_school_code"] = school_code
        return payload

    if role == "parent":
        parent_id = _to_int(profile.get("parent_id"))
        if parent_id is None:
            return None
        payload.update(
            {
                "auth_role": "parent",
                "auth_login": (
                    auth_login
                    or _text(profile.get("full_name"))
                    or _text(profile.get("telegram_username"))
                    or f"parent-{parent_id}"
                ),
                "parent_id": parent_id,
                "parent_full_name": _text(profile.get("full_name")),
            }
        )
        telegram_user_id = _to_int(profile.get("telegram_user_id"))
        if telegram_user_id is not None:
            payload["telegram_user_id"] = telegram_user_id
        return payload

    if role == "teacher":
        teacher_id = _to_int(profile.get("teacher_id"))
        staff_id = _to_int(profile.get("staff_id"))
        if teacher_id is None and staff_id is None:
            return None
        teacher_code = _text(profile.get("teacher_code")) or auth_login
        payload.update(
            {
                "auth_role": "teacher",
                "auth_login": teacher_code,
                "teacher_id": teacher_id,
                "staff_id": staff_id,
                "teacher_full_name": _text(profile.get("full_name")),
            }
        )
        return payload

    if role in STAFF_ACCOUNT_ROLES:
        staff_id = _to_int(profile.get("staff_id"))
        if staff_id is None:
            return None
        payload.update(
            {
                "auth_role": role,
                "staff_id": staff_id,
                "staff_role": role,
            }
        )
        if role == "system_admin":
            payload.update(
                {
                    "auth_role": "admin",
                    "admin_id": staff_id,
                    "admin_role": "owner" if profile.get("is_owner") else "system_admin",
                    "admin_is_owner": bool(profile.get("is_owner")),
                    "admin_last_panel": "overview",
                    "admin_last_school": "all",
                }
            )
        return payload
    return None


def load_account_auth_result(
    account_id: Any,
    conn: Any | None = None,
    *,
    record_login: bool = False,
) -> dict[str, Any] | None:
    """Build a canonical session only for an active account and active profile."""

    def _load(active_conn: Any) -> dict[str, Any] | None:
        account = get_account_by_id(account_id, conn=active_conn)
        if not account:
            return None
        role = normalize_role(account.get("role"))
        if role not in ACCOUNT_AUTH_ROLES:
            return None
        if _text(account.get("status")).casefold() != PASSWORD_LOGIN_ALLOWED_STATUS:
            return None
        profile = load_account_profile(account, conn=active_conn)
        if not _profile_allows_login(profile):
            return None
        session_payload = build_session_payload(account, profile)
        if not session_payload:
            return None
        if record_login and (
            conn is None or getattr(active_conn, "db_backend", "") == "postgres"
        ):
            repository.mark_account_login(active_conn, int(account["id"]))
        return {
            "account": account,
            "profile": profile,
            "session": session_payload,
        }

    return _with_connection(conn, _load)


# Compatibility name for route/session callers during the page-router cutover.
build_legacy_session_payload = build_session_payload


def authenticate_account_password(
    login: Any,
    password: Any,
    conn: Any | None = None,
) -> dict[str, Any] | None:
    normalized_login = normalize_login(login)

    def _reject(reason: str) -> None:
        LOGGER.warning(
            "password_auth_rejected login=%s reason=%s password_length=%s",
            normalized_login,
            reason,
            len(str(password or "")),
        )
        return None

    def _authenticate(active_conn: Any) -> dict[str, Any] | None:
        account = get_account_by_login(login, conn=active_conn)
        if not account:
            return _reject("account_missing")
        role = normalize_role(account.get("role"))
        if role not in ACCOUNT_AUTH_ROLES:
            return _reject("role_not_allowed")
        if _text(account.get("status")).casefold() != PASSWORD_LOGIN_ALLOWED_STATUS:
            return _reject("account_inactive")
        if not verify_account_password(account, password):
            return _reject("password_mismatch")
        profile = load_account_profile(account, conn=active_conn)
        if not _profile_allows_login(profile):
            return _reject("profile_inactive")
        session_payload = build_session_payload(account, profile)
        if not session_payload:
            return _reject("session_payload_invalid")
        # Unit-test connection doubles intentionally do not advertise a backend.
        # Real connections record login time in the same transaction.
        if conn is None or getattr(active_conn, "db_backend", "") == "postgres":
            repository.mark_account_login(active_conn, int(account["id"]))
        return {"account": account, "profile": profile, "session": session_payload}

    return _with_connection(conn, _authenticate)


def _password_validation(
    *,
    current_password: str,
    new_password: str,
    confirm_password: str,
) -> PasswordChangeOutcome | None:
    if not current_password:
        return PasswordChangeOutcome(False, "Current password is required.", "current_password_required")
    if not new_password:
        return PasswordChangeOutcome(False, "New password is required.", "new_password_required")
    if len(new_password) < MIN_PASSWORD_LENGTH:
        return PasswordChangeOutcome(
            False,
            f"New password must be at least {MIN_PASSWORD_LENGTH} characters.",
            "password_too_short",
        )
    if new_password != confirm_password:
        return PasswordChangeOutcome(False, "New password and confirmation do not match.", "password_mismatch")
    if current_password == new_password:
        return PasswordChangeOutcome(
            False,
            "New password must be different from current password.",
            "password_unchanged",
        )
    return None


def _change_locked_account_password(
    conn: Any,
    *,
    account: dict[str, Any] | None,
    current_password: str,
    new_password: str,
    actor_account_id: int,
) -> PasswordChangeOutcome:
    if not account or _text(account.get("status")).casefold() != "active":
        return PasswordChangeOutcome(False, "Account was not found or is disabled.", "account_unavailable")
    if not verify_account_password(account, current_password):
        return PasswordChangeOutcome(False, "Current password is incorrect.", "current_password_incorrect")
    account_id = int(account["id"])
    session_version = repository.change_account_password(
        conn,
        account_id=account_id,
        password_hash=generate_password_hash(new_password),
        must_change_password=False,
    )
    if session_version <= 0:
        return PasswordChangeOutcome(False, "Unable to change password.", "password_update_failed")
    repository.insert_account_audit_event(
        conn,
        actor_account_id=actor_account_id,
        event_type="account.password_changed",
        entity_account_id=account_id,
        detail={"role": normalize_role(account.get("role")), "method": "self_service"},
    )
    return PasswordChangeOutcome(True, session_version=session_version)


def change_own_password(
    account_id: Any,
    *,
    current_password: Any,
    new_password: Any,
    confirm_password: Any,
    conn: Any | None = None,
) -> PasswordChangeOutcome:
    parsed_account_id = _to_int(account_id)
    if parsed_account_id is None:
        return PasswordChangeOutcome(False, "Canonical account session is required.", "account_session_required")
    current_value = str(current_password or "")
    new_value = str(new_password or "")
    confirm_value = str(confirm_password or "")
    invalid = _password_validation(
        current_password=current_value,
        new_password=new_value,
        confirm_password=confirm_value,
    )
    if invalid:
        return invalid

    def _change(active_conn: Any) -> PasswordChangeOutcome:
        account = _normalize_account(
            repository.get_account_by_id_row(active_conn, parsed_account_id, for_update=True)
        )
        return _change_locked_account_password(
            active_conn,
            account=account,
            current_password=current_value,
            new_password=new_value,
            actor_account_id=parsed_account_id,
        )

    if conn is not None:
        return _change(conn)
    with DB_LOCK:
        return _with_connection(None, _change)


def reset_student_password(
    student_row_id: Any,
    new_password: Any,
    *,
    actor_account_id: Any = None,
    conn: Any | None = None,
) -> PasswordChangeOutcome:
    parsed_student_id = _to_int(student_row_id)
    if parsed_student_id is None:
        return PasswordChangeOutcome(False, "Invalid student.", "invalid_student")
    new_value = str(new_password or "")
    if not new_value:
        return PasswordChangeOutcome(False, "New password is required.", "new_password_required")
    if len(new_value) < MIN_PASSWORD_LENGTH:
        return PasswordChangeOutcome(
            False,
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters.",
            "password_too_short",
        )
    parsed_actor_id = _to_int(actor_account_id)

    def _reset(active_conn: Any) -> PasswordChangeOutcome:
        account = _normalize_account(
            repository.get_student_account_by_legacy_id_row(
                active_conn,
                parsed_student_id,
                for_update=True,
            )
        )
        if not account:
            return PasswordChangeOutcome(False, "Student account was not found.", "account_unavailable")
        account_id = int(account["id"])
        session_version = repository.change_account_password(
            active_conn,
            account_id=account_id,
            password_hash=generate_password_hash(new_value),
            must_change_password=True,
        )
        repository.insert_account_audit_event(
            active_conn,
            actor_account_id=parsed_actor_id,
            event_type="account.password_reset",
            entity_account_id=account_id,
            detail={"role": "student", "method": "administrator"},
        )
        return PasswordChangeOutcome(bool(session_version), session_version=session_version)

    if conn is not None:
        return _reset(conn)
    with DB_LOCK:
        return _with_connection(None, _reset)


def reset_linked_account_password(
    conn: Any,
    *,
    account_id: Any,
    temporary_password: Any,
) -> int:
    """Reset a linked canonical account inside a caller-owned transaction."""

    parsed_account_id = _to_int(account_id)
    password_value = str(temporary_password or "")
    if parsed_account_id is None or len(password_value) < MIN_PASSWORD_LENGTH:
        return 0
    return repository.reset_account_password(
        conn,
        account_id=parsed_account_id,
        password_hash=generate_password_hash(password_value),
    )


def provision_student_account(
    conn: Any,
    *,
    student_id: int,
    login: str,
    initial_password: str,
    full_name: str,
    school_id: int | None,
    status: str = "active",
) -> int:
    normalized_login = _text(login).upper()
    if not normalized_login or not initial_password:
        return 0
    current = _row_to_dict(
        repository.find_student_account_row(
            conn,
            student_id=int(student_id),
            login=normalized_login,
        )
    )
    return repository.save_student_account(
        conn,
        account_id=int(current["id"] or 0) if current else 0,
        student_id=int(student_id),
        login=normalized_login,
        password_hash=generate_password_hash(initial_password),
        full_name=_text(full_name),
        school_id=school_id,
        status=_text(status).casefold() or "active",
    )


def provision_teacher_account(
    conn: Any,
    *,
    teacher_id: int,
    staff_id: int,
    full_name: str,
    canonical_login: str = "",
    legacy_login: str = "",
    status: str = "active",
) -> tuple[int, str]:
    login = _text(canonical_login).upper() or repository.get_next_teacher_code(conn)
    current = _row_to_dict(
        repository.find_teacher_account_row(
            conn,
            teacher_id=int(teacher_id),
            staff_id=int(staff_id),
            login=login,
        )
    )
    account_id = repository.save_teacher_account(
        conn,
        account_id=int(current["id"] or 0) if current else 0,
        teacher_id=int(teacher_id),
        staff_id=int(staff_id),
        login=login,
        legacy_login=_text(legacy_login),
        password_hash=generate_password_hash(login),
        full_name=_text(full_name),
        status=_text(status).casefold() or "active",
    )
    return account_id, login


def synchronize_staff_account(
    conn: Any,
    *,
    staff_id: int,
    login: str,
    password_hash: str,
    role: str,
    full_name: str,
    phone: str = "",
    job_title: str = "",
    department: str = "",
    must_change_password: bool | None = None,
) -> int:
    normalized_login = _text(login)
    normalized_role = normalize_role(role)
    if not normalized_login or normalized_role not in STAFF_ACCOUNT_ROLES:
        return 0
    current = _row_to_dict(
        repository.find_staff_account_row(
            conn,
            staff_id=int(staff_id),
            login=normalized_login,
        )
    )
    force_change = (
        verify_password_hash(password_hash, normalized_login)
        if must_change_password is None
        else bool(must_change_password)
    )
    return repository.save_staff_account(
        conn,
        account_id=int(current["id"] or 0) if current else 0,
        staff_id=int(staff_id),
        login=normalized_login,
        password_hash=password_hash,
        role=normalized_role,
        full_name=_text(full_name) or normalized_login,
        phone=_text(phone),
        job_title=_text(job_title) or normalized_role.replace("_", " ").title(),
        department=_text(department) or normalized_role.replace("_", " ").title(),
        must_change_password=force_change,
    )


def provision_parent_account(
    conn: Any,
    *,
    parent_id: int,
    full_name: str,
    phone: str = "",
    telegram_user_id: Any = None,
    telegram_username: str = "",
) -> int:
    """Provision the Telegram-only canonical account for a parent claim."""

    parsed_parent_id = _to_int(parent_id)
    if parsed_parent_id is None:
        return 0
    parsed_telegram_id = _to_int(telegram_user_id)
    current = _row_to_dict(
        repository.find_parent_account_row(conn, parent_id=parsed_parent_id)
    )
    return repository.save_parent_account(
        conn,
        account_id=int(current["id"] or 0) if current else 0,
        parent_id=parsed_parent_id,
        full_name=_text(full_name),
        phone=_text(phone),
        telegram_user_id=parsed_telegram_id,
        telegram_username=_text(telegram_username).lstrip("@"),
    )


def claim_parent_telegram_identity(
    conn: Any,
    *,
    parent_id: int,
    full_name: str,
    phone: str = "",
    telegram_user_id: Any,
    telegram_username: str = "",
) -> int:
    """Atomically transfer a verified Telegram user to a canonical parent."""

    parsed_parent_id = _to_int(parent_id)
    parsed_telegram_id = _to_int(telegram_user_id)
    if parsed_parent_id is None or parsed_telegram_id is None:
        return 0
    normalized_username = _text(telegram_username).lstrip("@")
    repository.transfer_parent_telegram_identity(
        conn,
        parent_id=parsed_parent_id,
        telegram_user_id=parsed_telegram_id,
        telegram_username=normalized_username,
    )
    return provision_parent_account(
        conn,
        parent_id=parsed_parent_id,
        full_name=full_name,
        phone=phone,
        telegram_user_id=parsed_telegram_id,
        telegram_username=normalized_username,
    )


__all__ = [
    "ACCOUNT_AUTH_ROLES",
    "MIN_PASSWORD_LENGTH",
    "PASSWORD_LOGIN_ALLOWED_STATUS",
    "PasswordChangeOutcome",
    "authenticate_account_password",
    "build_legacy_session_payload",
    "build_session_payload",
    "claim_parent_telegram_identity",
    "change_own_password",
    "get_account_by_id",
    "get_account_by_login",
    "load_account_auth_result",
    "load_account_profile",
    "normalize_login",
    "provision_student_account",
    "provision_parent_account",
    "provision_teacher_account",
    "reset_student_password",
    "reset_linked_account_password",
    "synchronize_staff_account",
    "verify_account_password",
]
