"""Staff account registration services."""

from __future__ import annotations

import secrets
from typing import Any

from backend.core.database import connect_auth_db
from backend.core.access.roles import normalize_role
from backend.modules.domains.identity.passwords import generate_password_hash

from backend.modules.domains.identity import staff_repository as repository


HR_MANAGER_LOGIN = "HR0001"
CUSTOMER_SUPPORT_LOGIN = "cs0001"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _to_int(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return parsed if parsed > 0 else 0


def _utc_now_iso():
    from datetime import UTC, datetime

    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _generate_temporary_password(length: int = 12) -> str:
    """Return an unambiguous, human-shareable one-time password."""

    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
    return "".join(secrets.choice(alphabet) for _ in range(max(8, length)))


def list_active_subjects() -> list[dict[str, Any]]:
    """Subject options for the Head of Departments page (New HOD form + coverage).

    Best-effort: the page must still render when the subjects table (or the
    database itself) is unavailable, so failures collapse to an empty list.
    """
    try:
        with connect_auth_db() as conn:
            return repository._list_active_subjects(conn)
    except Exception:
        return []


def create_hr_manager_account(
    *,
    display_name: str = "HR Manager",
) -> tuple[bool, str, dict[str, Any]]:
    """Create or reset the single standalone HR Manager identity."""

    with connect_auth_db() as conn:
        return _create_hr_manager_account(
            conn,
            display_name=display_name,
            commit=True,
        )


def _create_hr_manager_account(
    conn: Any,
    *,
    display_name: str = "HR Manager",
    commit: bool = False,
) -> tuple[bool, str, dict[str, Any]]:
    if not repository._phase1_accounts_available(conn):
        return False, "Shared accounts are not available. Apply the account schema first.", {}

    login = HR_MANAGER_LOGIN
    normalized_display_name = _text(display_name) or "HR Manager"
    staff = repository._staff_identity_by_login(conn, login)
    if staff and normalize_role(staff["role"]) != "hr_manager":
        return False, f"{login} already belongs to another staff role.", {}

    account_by_login = repository._account_identity_by_login(conn, login)
    if account_by_login and normalize_role(account_by_login["role"]) != "hr_manager":
        return False, f"{login} already belongs to another account role.", {}

    staff_id = _to_int(staff["id"]) if staff else 0
    account_by_staff = (
        repository._account_identity_by_staff_id(conn, staff_id) if staff_id else None
    )
    if account_by_staff and normalize_role(account_by_staff["role"]) != "hr_manager":
        return False, "The linked staff identity belongs to another account role.", {}
    if (
        account_by_login
        and account_by_staff
        and _to_int(account_by_login["id"]) != _to_int(account_by_staff["id"])
    ):
        return False, f"{login} is linked to conflicting account records.", {}

    password = login
    password_hash = generate_password_hash(password)
    now = _utc_now_iso()
    existing_account = account_by_login or account_by_staff

    staff_id = repository._insert_or_update_staff_role(
        conn,
        login=login,
        password_hash=password_hash,
        display_name=normalized_display_name,
        role="hr_manager",
        subject_scope="",
        now=now,
    )
    if not staff_id:
        conn.rollback()
        return False, "Unable to create the HR Manager staff row.", {}

    account_id = repository._upsert_staff_account(
        conn,
        staff_id=staff_id,
        login=login,
        password_hash=password_hash,
        display_name=normalized_display_name,
        role="hr_manager",
        must_change_password=False,
        now=now,
    )
    if not account_id:
        conn.rollback()
        return False, "Unable to create the HR Manager account.", {}

    profile_id = repository._upsert_staff_profile_role(
        conn,
        account_id=account_id,
        staff_id=staff_id,
        job_title="HR Manager",
        department="Human Resources",
        now=now,
    )
    if not profile_id:
        conn.rollback()
        return False, "Unable to create the HR Manager profile.", {}

    repository._insert_account_audit_event(
        conn,
        event_type="account.password_reset" if existing_account else "account.created",
        entity_account_id=account_id,
        detail={"role": "hr_manager", "method": "operator_cli"},
    )
    if commit:
        conn.commit()

    return True, "", {
        "role": "hr_manager",
        "login": login,
        "temporary_password": password,
        "display_name": normalized_display_name,
        "must_change_password": False,
        "account_id": account_id,
        "staff_id": staff_id,
    }


def create_customer_support_account(
    *,
    display_name: str = "Customer Support",
) -> tuple[bool, str, dict[str, Any]]:
    """Create or reset the fixed standalone Customer Support identity."""

    with connect_auth_db() as conn:
        return _create_customer_support_account(
            conn,
            display_name=display_name,
            commit=True,
        )


def _create_customer_support_account(
    conn: Any,
    *,
    display_name: str = "Customer Support",
    commit: bool = False,
) -> tuple[bool, str, dict[str, Any]]:
    if not repository._phase1_accounts_available(conn):
        return False, "Shared accounts are not available. Apply the account schema first.", {}

    login = CUSTOMER_SUPPORT_LOGIN
    normalized_display_name = _text(display_name) or "Customer Support"
    staff = repository._staff_identity_by_login(conn, login)
    if staff and normalize_role(staff["role"]) != "customer_support":
        return False, f"{login} already belongs to another staff role.", {}

    account_by_login = repository._account_identity_by_login(conn, login)
    if account_by_login and normalize_role(account_by_login["role"]) != "customer_support":
        return False, f"{login} already belongs to another account role.", {}

    staff_id = _to_int(staff["id"]) if staff else 0
    account_by_staff = (
        repository._account_identity_by_staff_id(conn, staff_id) if staff_id else None
    )
    if account_by_staff and normalize_role(account_by_staff["role"]) != "customer_support":
        return False, "The linked staff identity belongs to another account role.", {}
    if (
        account_by_login
        and account_by_staff
        and _to_int(account_by_login["id"]) != _to_int(account_by_staff["id"])
    ):
        return False, f"{login} is linked to conflicting account records.", {}

    password = login
    password_hash = generate_password_hash(password)
    now = _utc_now_iso()
    existing_account = account_by_login or account_by_staff

    staff_id = repository._insert_or_update_staff_role(
        conn,
        login=login,
        password_hash=password_hash,
        display_name=normalized_display_name,
        role="customer_support",
        subject_scope="",
        now=now,
    )
    if not staff_id:
        conn.rollback()
        return False, "Unable to create the Customer Support staff row.", {}

    account_id = repository._upsert_staff_account(
        conn,
        staff_id=staff_id,
        login=login,
        password_hash=password_hash,
        display_name=normalized_display_name,
        role="customer_support",
        must_change_password=False,
        now=now,
    )
    if not account_id:
        conn.rollback()
        return False, "Unable to create the Customer Support account.", {}

    profile_id = repository._upsert_staff_profile_role(
        conn,
        account_id=account_id,
        staff_id=staff_id,
        job_title="Customer Support",
        department="Customer Support",
        now=now,
    )
    if not profile_id:
        conn.rollback()
        return False, "Unable to create the Customer Support profile.", {}

    repository._insert_account_audit_event(
        conn,
        event_type="account.password_reset" if existing_account else "account.created",
        entity_account_id=account_id,
        detail={"role": "customer_support", "method": "operator_cli"},
    )
    if commit:
        conn.commit()

    return True, "", {
        "role": "customer_support",
        "login": login,
        "temporary_password": password,
        "display_name": normalized_display_name,
        "must_change_password": False,
        "account_id": account_id,
        "staff_id": staff_id,
    }


def create_head_of_department_account(
    *,
    display_name: str,
    subject_id: Any,
    created_by: str = "",
) -> tuple[bool, str, dict[str, Any]]:
    with connect_auth_db() as conn:
        return _create_head_of_department_account(
            conn,
            display_name=display_name,
            subject_id=subject_id,
            created_by=created_by,
            commit=True,
        )


def reset_head_of_department_password(
    account_id: Any,
    *,
    actor_account_id: Any = None,
    actor_login: str = "",
) -> tuple[bool, str, dict[str, Any]]:
    with connect_auth_db() as conn:
        return _reset_head_of_department_password(
            conn,
            account_id=account_id,
            actor_account_id=actor_account_id,
            actor_login=actor_login,
            commit=True,
        )


def _reset_head_of_department_password(
    conn: Any,
    *,
    account_id: Any,
    actor_account_id: Any = None,
    actor_login: str = "",
    commit: bool = False,
) -> tuple[bool, str, dict[str, Any]]:
    parsed_account_id = _to_int(account_id)
    if not parsed_account_id:
        return False, "Head of Department account was not found.", {}

    account = repository.lock_head_of_department_account(conn, parsed_account_id)
    if not account:
        return False, "Head of Department account was not found.", {}
    if _text(account["status"]).casefold() != "active":
        return False, "Head of Department account is disabled.", {}

    login = _text(account["login"])
    if not login:
        return False, "Head of Department account has no login.", {}

    temporary_password = _generate_temporary_password()
    password_hash = generate_password_hash(temporary_password)
    now = _utc_now_iso()
    updated = repository.update_head_of_department_password(
        conn,
        account_id=parsed_account_id,
        password_hash=password_hash,
        updated_at=now,
    )
    if not updated:
        return False, "Unable to reset the Head of Department password.", {}

    legacy_staff_id = _to_int(account["legacy_source_id"])
    repository.update_legacy_head_of_department_password(
        conn,
        legacy_staff_id=legacy_staff_id,
        login=login,
        password_hash=password_hash,
        updated_at=now,
    )
    repository._insert_password_reset_audit_event(
        conn,
        actor_account_id=_to_int(actor_account_id) or None,
        entity_account_id=parsed_account_id,
        actor_login=actor_login,
    )

    if commit:
        conn.commit()

    return True, "", {
        "login": login,
        "temporary_password": temporary_password,
        "display_name": _text(account["full_name"]) or login,
        "must_change_password": True,
        "updated_at": now,
    }


def list_head_of_department_accounts() -> dict[str, Any]:
    with connect_auth_db() as conn:
        return repository._list_head_of_department_accounts(conn)


def create_academic_director_account(
    *,
    login: str = "AD0001",
    display_name: str = "Academic Director",
    temporary_password: str = "",
    commit: bool = True,
) -> tuple[bool, str, dict[str, Any]]:
    with connect_auth_db() as conn:
        return _create_academic_director_account(
            conn,
            login=login,
            display_name=display_name,
            temporary_password=temporary_password,
            commit=commit,
        )


def _create_academic_director_account(
    conn: Any,
    *,
    login: str = "AD0001",
    display_name: str = "Academic Director",
    temporary_password: str = "",
    commit: bool = False,
) -> tuple[bool, str, dict[str, Any]]:
    if not repository._phase1_accounts_available(conn):
        return False, "Shared accounts are not available. Apply Phase 1 account schema first.", {}

    normalized_login = _text(login).upper() or "AD0001"
    if not normalized_login.startswith("AD"):
        return False, "Academic Director login must use AD0001 format.", {}
    # Newly issued credentials are predictable only for the first sign-in:
    # login and initial password match, then the account is forced to change it.
    password = normalized_login
    normalized_display_name = _text(display_name) or "Academic Director"
    now = _utc_now_iso()
    password_hash = generate_password_hash(password)

    staff_id = repository._insert_or_update_staff_role(
        conn,
        login=normalized_login,
        password_hash=password_hash,
        display_name=normalized_display_name,
        role="academic_director",
        subject_scope="",
        now=now,
    )
    if not staff_id:
        return False, "Unable to create Academic Director staff row.", {}

    account_id = repository._upsert_staff_account(
        conn,
        staff_id=staff_id,
        login=normalized_login,
        password_hash=password_hash,
        display_name=normalized_display_name,
        role="academic_director",
        now=now,
    )
    if not account_id:
        return False, "Unable to create Academic Director account.", {}

    profile_id = repository._upsert_staff_profile_role(
        conn,
        account_id=account_id,
        staff_id=staff_id,
        job_title="Academic Director",
        department="Academic Department",
        now=now,
    )
    if not profile_id:
        return False, "Unable to create Academic Director profile.", {}

    if commit:
        conn.commit()

    return True, "", {
        "role": "academic_director",
        "login": normalized_login,
        "temporary_password": password,
        "display_name": normalized_display_name,
        "account_id": account_id,
        "staff_id": staff_id,
    }


def _create_head_of_department_account(
    conn: Any,
    *,
    display_name: str,
    subject_id: Any,
    created_by: str = "",
    commit: bool = False,
) -> tuple[bool, str, dict[str, Any]]:
    if not repository._phase1_accounts_available(conn):
        return False, "Shared accounts are not available. Apply Phase 1 account schema first.", {}

    subject = repository._subject_row(conn, subject_id)
    if not subject:
        return False, "Select a valid subject scope.", {}

    subject_name = _text(subject.get("subject_name")) or "Department"
    subject_key = _text(subject.get("subject_key"))
    normalized_display_name = _text(display_name) or f"Head of {subject_name} Department"
    now = _utc_now_iso()
    login = repository._next_staff_code(conn, "HOD")
    password_hash = generate_password_hash(login)

    staff_id = repository._insert_or_update_hod_staff(
        conn,
        login=login,
        password_hash=password_hash,
        display_name=normalized_display_name,
        subject_key=subject_key or str(subject["id"]),
        actor_login=_text(created_by),
        now=now,
    )
    if not staff_id:
        return False, "Unable to create HOD staff row.", {}

    account_id = repository._upsert_hod_account(
        conn,
        staff_id=staff_id,
        login=login,
        password_hash=password_hash,
        display_name=normalized_display_name,
        now=now,
    )
    if not account_id:
        return False, "Unable to create HOD account.", {}

    profile_id = repository._upsert_hod_profile(
        conn,
        account_id=account_id,
        staff_id=staff_id,
        department=f"{subject_name} Department",
        subject_id=int(subject["id"]),
        now=now,
    )
    if not profile_id:
        return False, "Unable to create HOD profile.", {}

    if commit:
        conn.commit()

    credentials = {
        "role": "head_of_department",
        "login": login,
        "temporary_password": login,
        "display_name": normalized_display_name,
        "subject_id": int(subject["id"]),
        "subject_name": subject_name,
        "account_id": account_id,
        "staff_id": staff_id,
    }
    return True, "", credentials
