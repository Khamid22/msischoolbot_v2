"""Shared-account password auth helpers.

This module reads the Phase 1 ``msi_v2.accounts`` tables and builds
route-compatible session payloads for account/profile password login.
"""

from __future__ import annotations

from typing import Any, Callable

from backend.core.security import verify_password_hash
from backend.identity.common import connect
from backend.identity.roles import normalize_role
from database.academics.canonical import normalize_school_code


PASSWORD_LOGIN_ALLOWED_STATUS = "active"
ACCOUNT_AUTH_ROLES = {
    "system_admin",
    "ceo",
    "hr_manager",
    "customer_support",
    "student",
    "teacher",
    "parent",
    "academic_director",
    "head_of_department",
}
STAFF_ACCOUNT_ROLES = {
    "system_admin",
    "ceo",
    "hr_manager",
    "customer_support",
    "academic_director",
    "head_of_department",
}

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


def _row_to_dict(row: Any) -> dict[str, Any] | None:
    if not row:
        return None
    return dict(row)


def _with_connection(conn: Any | None, callback: Callable[[Any], Any]) -> Any:
    if conn is not None:
        return callback(conn)
    with connect() as opened_conn:
        return callback(opened_conn)


def _fetchone(conn: Any, sql: str, params: tuple[Any, ...]) -> dict[str, Any] | None:
    return _row_to_dict(conn.execute(sql, params).fetchone())


def _normalize_account(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    account_id = _to_int(row.get("id"))
    if account_id is None:
        return None
    role = normalize_role(row.get("role"))
    return {
        "id": account_id,
        "login": _text(row.get("login")) or None,
        "password_hash": _text(row.get("password_hash")) or None,
        "role": role,
        "raw_role": _text(row.get("role")),
        "status": _text(row.get("status")).casefold() or "disabled",
        "full_name": _text(row.get("full_name")),
        "phone": _text(row.get("phone")) or None,
        "legacy_source_table": _text(row.get("legacy_source_table")),
        "legacy_source_id": _to_int(row.get("legacy_source_id")),
    }


def get_account_by_login(login: Any, conn: Any | None = None) -> dict[str, Any] | None:
    normalized_login = normalize_login(login)
    if not normalized_login:
        return None

    def _load(active_conn: Any) -> dict[str, Any] | None:
        row = _fetchone(
            active_conn,
            """
            SELECT id, login, password_hash, role, status, full_name, phone,
                   legacy_source_table, legacy_source_id
            FROM msi_v2.accounts
            WHERE lower(btrim(login)) = lower(btrim(%s))
            LIMIT 1
            """,
            (normalized_login,),
        )
        return _normalize_account(row)

    return _with_connection(conn, _load)


def verify_account_password(account: dict[str, Any] | None, password: Any) -> bool:
    if not account:
        return False
    return verify_password_hash(account.get("password_hash"), password)


def _student_profile(conn: Any, account_id: int) -> dict[str, Any] | None:
    row = _fetchone(
        conn,
        """
        SELECT sp.id AS profile_id, sp.account_id, sp.student_id, sp.school_id,
               sp.student_code, sp.class_id, sp.status AS profile_status,
               COALESCE(st.legacy_student_row_id, st.id) AS legacy_student_row_id,
               st.full_name,
               COALESCE(NULLIF(st.student_code, ''), sp.student_code) AS current_student_code,
               COALESCE(sch.school_key, '') AS school_code,
               COALESCE(
                   (
                       SELECT min(gs.legacy_public_dashboard_id)
                       FROM msi_v2.group_students gs
                       WHERE gs.student_id = st.id
                         AND gs.enrollment_status = 'active'
                         AND gs.legacy_public_dashboard_id IS NOT NULL
                   ),
                   st.legacy_public_dashboard_id
               ) AS enrollment_id
        FROM msi_v2.student_profiles sp
        JOIN msi_v2.students st ON st.id = sp.student_id
        LEFT JOIN msi_v2.schools sch ON sch.id = st.school_id
        WHERE sp.account_id = %s
        LIMIT 1
        """,
        (account_id,),
    )
    if not row:
        return None
    return {
        "role": "student",
        "profile_id": _to_int(row.get("profile_id")),
        "account_id": _to_int(row.get("account_id")),
        "student_id": _to_int(row.get("student_id")),
        "student_db_id": _to_int(row.get("legacy_student_row_id")),
        "student_code": _text(row.get("current_student_code") or row.get("student_code")),
        "student_enrollment_id": _to_int(row.get("enrollment_id")),
        "full_name": _text(row.get("full_name")),
        "school_code": normalize_school_code(row.get("school_code"), default=""),
        "status": _text(row.get("profile_status")).casefold() or "disabled",
    }


def _teacher_profile(conn: Any, account_id: int) -> dict[str, Any] | None:
    row = _fetchone(
        conn,
        """
        SELECT tp.id AS profile_id, tp.account_id, tp.teacher_id, tp.school_id,
               tp.teacher_code, tp.legacy_login, tp.status AS profile_status,
               t.full_name,
               staff.id AS teacher_staff_id,
               COALESCE(g.group_name, '') AS assigned_group
        FROM msi_v2.teacher_profiles tp
        JOIN msi_v2.teachers t ON t.id = tp.teacher_id
        LEFT JOIN msi_v2.msi_staff staff
          ON staff.teacher_id = tp.teacher_id
         AND lower(staff.role) = 'teacher'
        LEFT JOIN msi_v2.group_teachers gt
          ON gt.teacher_id = tp.teacher_id
         AND gt.status = 'active'
         AND gt.role = 'main'
        LEFT JOIN msi_v2.groups g ON g.id = gt.group_id
        WHERE tp.account_id = %s
        ORDER BY
            CASE WHEN lower(COALESCE(staff.status, '')) = 'active' THEN 0 ELSE 1 END,
            staff.id NULLS LAST
        LIMIT 1
        """,
        (account_id,),
    )
    if not row:
        return None
    return {
        "role": "teacher",
        "profile_id": _to_int(row.get("profile_id")),
        "account_id": _to_int(row.get("account_id")),
        "teacher_id": _to_int(row.get("teacher_id")),
        "teacher_staff_id": _to_int(row.get("teacher_staff_id")),
        "teacher_code": _text(row.get("teacher_code")),
        "legacy_login": _text(row.get("legacy_login")),
        "full_name": _text(row.get("full_name")),
        "assigned_group": _text(row.get("assigned_group")),
        "status": _text(row.get("profile_status")).casefold() or "disabled",
    }


def _parent_profile(conn: Any, account_id: int) -> dict[str, Any] | None:
    row = _fetchone(
        conn,
        """
        SELECT pp.id AS profile_id, pp.account_id, pp.parent_id,
               pp.telegram_username, pp.status AS profile_status,
               p.display_name AS full_name, p.telegram_user_id
        FROM msi_v2.parent_profiles pp
        JOIN msi_v2.parents p ON p.id = pp.parent_id
        WHERE pp.account_id = %s
        LIMIT 1
        """,
        (account_id,),
    )
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
    row = _fetchone(
        conn,
        """
        SELECT sp.id AS profile_id, sp.account_id, sp.staff_id, sp.job_title,
               sp.department, sp.status AS profile_status,
               staff.login AS staff_login,
               staff.role AS legacy_staff_role,
               CASE WHEN lower(COALESCE(staff.role, '')) = 'owner' THEN 1 ELSE 0 END AS is_owner
        FROM msi_v2.staff_profiles sp
        LEFT JOIN msi_v2.msi_staff staff ON staff.id = sp.staff_id
        WHERE sp.account_id = %s
        LIMIT 1
        """,
        (account_id,),
    )
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


def load_account_profile(account: dict[str, Any] | None, conn: Any | None = None) -> dict[str, Any] | None:
    if not account:
        return None
    account_id = _to_int(account.get("id"))
    role = normalize_role(account.get("role"))
    if account_id is None or role not in ACCOUNT_AUTH_ROLES:
        return None

    def _load(active_conn: Any) -> dict[str, Any] | None:
        if role == "student":
            return _student_profile(active_conn, account_id)
        if role == "teacher":
            return _teacher_profile(active_conn, account_id)
        if role == "parent":
            return _parent_profile(active_conn, account_id)
        if role in STAFF_ACCOUNT_ROLES:
            return _staff_profile(active_conn, account_id, role)
        return None

    return _with_connection(conn, _load)


def _profile_allows_password_login(profile: dict[str, Any] | None) -> bool:
    return bool(profile and _text(profile.get("status")).casefold() == PASSWORD_LOGIN_ALLOWED_STATUS)


def build_legacy_session_payload(
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

    if role == "teacher":
        teacher_id = _to_int(profile.get("teacher_id"))
        teacher_code = _text(profile.get("teacher_code")) or auth_login
        if teacher_id is None or not teacher_code:
            return None
        payload.update(
            {
                "auth_role": "teacher",
                "auth_login": teacher_code,
                "teacher_id": teacher_id,
                "teacher_full_name": _text(profile.get("full_name")),
                "teacher_group": _text(profile.get("assigned_group")),
            }
        )
        teacher_staff_id = _to_int(profile.get("teacher_staff_id"))
        if teacher_staff_id is not None:
            payload["teacher_staff_id"] = teacher_staff_id
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
            # Temporary compatibility: legacy /admin routes still check
            # auth_role == "admin". Keep canonical role metadata for future
            # Auth V2 routes while allowing current admin screens to work.
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


def authenticate_account_password(
    login: Any,
    password: Any,
    conn: Any | None = None,
) -> dict[str, Any] | None:
    account = get_account_by_login(login, conn=conn)
    if not account:
        return None
    role = normalize_role(account.get("role"))
    if role not in ACCOUNT_AUTH_ROLES:
        return None
    if _text(account.get("status")).casefold() != PASSWORD_LOGIN_ALLOWED_STATUS:
        return None
    if not verify_account_password(account, password):
        return None

    profile = load_account_profile(account, conn=conn)
    if not _profile_allows_password_login(profile):
        return None

    session_payload = build_legacy_session_payload(account, profile)
    if not session_payload:
        return None

    return {
        "account": account,
        "profile": profile,
        "session": session_payload,
    }


__all__ = [
    "authenticate_account_password",
    "build_legacy_session_payload",
    "get_account_by_login",
    "load_account_profile",
    "normalize_login",
    "verify_account_password",
]
