"""Opt-in demo authentication for team testing.

This module never disables sessions. It only pre-fills a normal session when
DEMO_AUTH_ENABLED=1, so production behavior stays unchanged when the flag is off.
"""

import os
import re

from backend.services.academics import canonical
from backend.core.database import connect_auth_db
from backend.services.identity.accounts import (
    build_session_payload,
    get_account_by_id,
    load_account_profile,
)

_TRUTHY = {"1", "true", "yes", "y", "on"}
_DASHBOARD_PATH_RE = re.compile(r"^/dashboard/(\d+)(?:/|$)")
_ADMIN_ROLE_ALLOWLIST = {
    "owner",
    "admin",
    "ceo",
    "academic_director",
    "head_of_department",
    "customer_support",
    "hr",
}


def is_demo_auth_enabled():
    return os.environ.get("DEMO_AUTH_ENABLED", "").strip().lower() in _TRUTHY


def _connect():
    return connect_auth_db()


def _apply_account_session(session, account_id, conn):
    account = get_account_by_id(account_id, conn=conn)
    profile = load_account_profile(account, conn=conn)
    payload = build_session_payload(account, profile)
    if not payload:
        return False
    # Demo auth is an explicit local/team-testing bypass and does not know the
    # user's initial password. Never trap a demo session in the password flow.
    payload["must_change_password"] = False
    payload["demo_auth"] = True
    session.clear()
    session.update(payload)
    return True


def _set_demo_student_session(session, *, enrollment_id, school_code=""):
    normalized_school_code = canonical.normalize_school_code(school_code)

    with _connect() as conn:
        row = conn.execute(
            """
            SELECT profile.account_id
            FROM msi_v2.group_students enrollment
            JOIN msi_v2.student_profiles profile
              ON profile.student_id = enrollment.student_id
            JOIN msi_v2.students student ON student.id = enrollment.student_id
            LEFT JOIN msi_v2.schools school ON school.id = student.school_id
            WHERE COALESCE(
                enrollment.legacy_public_dashboard_id,
                student.legacy_public_dashboard_id
            ) = %s
              AND (%s = '' OR lower(school.school_key) = lower(%s))
            LIMIT 1
            """,
            (int(enrollment_id), normalized_school_code, normalized_school_code),
        ).fetchone()
        if not row or not _apply_account_session(session, int(row["account_id"]), conn):
            return False
    session["student_enrollment_id"] = int(enrollment_id)
    if normalized_school_code:
        session["student_school_code"] = normalized_school_code
    return True


def _set_demo_admin_session(session):
    login = os.environ.get("DEMO_ADMIN_LOGIN", "").strip()
    demo_role = os.environ.get("DEMO_ADMIN_ROLE", "owner").strip().lower() or "owner"
    if demo_role not in _ADMIN_ROLE_ALLOWLIST:
        demo_role = "owner"
    canonical_role = {
        "owner": "system_admin",
        "admin": "system_admin",
        "hr": "hr_manager",
    }.get(demo_role, demo_role)

    with _connect() as conn:
        if login:
            row = conn.execute(
                """
                SELECT id FROM msi_v2.accounts
                WHERE lower(btrim(login)) = lower(btrim(%s))
                  AND role = %s AND status = 'active'
                LIMIT 1
                """,
                (login, canonical_role),
            ).fetchone()
        else:
            row = conn.execute(
                """
                SELECT id
                FROM msi_v2.accounts
                WHERE role = %s AND status = 'active'
                ORDER BY id ASC
                LIMIT 1
                """,
                (canonical_role,),
            ).fetchone()
        if not row or not _apply_account_session(session, int(row["id"]), conn):
            return False
    return True


def _set_demo_teacher_session(session):
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT account.id
            FROM msi_v2.accounts account
            JOIN msi_v2.teacher_profiles profile ON profile.account_id = account.id
            WHERE account.role = 'teacher'
              AND account.status = 'active'
              AND profile.status = 'active'
            ORDER BY account.id ASC
            LIMIT 1
            """
        ).fetchone()
        if not row or not _apply_account_session(session, int(row["id"]), conn):
            return False
    return True


def _is_admin_demo_path(path):
    return (
        path == "/"
        or path == "/admin"
        or path.startswith("/admin/")
    )


def _is_public_asset_or_auth_path(path):
    return (
        path.startswith("/static/")
        or path in {
            "/auth/telegram",
            "/login",
            "/logout",
            "/manifest.webmanifest",
            "/sw.js",
            "/docs",
            "/redoc",
            "/openapi.json",
        }
    )


def maybe_apply_demo_auth(request_obj):
    if not is_demo_auth_enabled():
        return False

    session = request_obj.session
    auth_role = str(session.get("auth_role", "")).strip().lower()
    is_demo_session = bool(session.get("demo_auth"))
    if auth_role and not is_demo_session:
        return False

    path = request_obj.url.path
    dashboard_match = _DASHBOARD_PATH_RE.match(path)
    if dashboard_match:
        return _set_demo_student_session(
            session,
            enrollment_id=int(dashboard_match.group(1)),
            school_code=request_obj.query_params.get("school", ""),
        )

    if path == "/teacher" or path.startswith("/teacher/"):
        if auth_role == "teacher" and is_demo_session:
            return False
        return _set_demo_teacher_session(session)

    if _is_admin_demo_path(path):
        if auth_role == "admin" and is_demo_session:
            return False
        return _set_demo_admin_session(session)

    if auth_role or _is_public_asset_or_auth_path(path):
        return False

    # Last-resort demo fallback for protected pages/APIs that are not tied to a
    # specific student dashboard URL. Student-specific write APIs keep the
    # student session created by /dashboard/<enrollment_id>.
    if path.startswith("/api/") or path.startswith("/profile/"):
        return _set_demo_admin_session(session)

    return False


__all__ = ["is_demo_auth_enabled", "maybe_apply_demo_auth"]
