"""Opt-in demo authentication for team testing.

This module never disables sessions. It only pre-fills a normal session when
DEMO_AUTH_ENABLED=1, so production behavior stays unchanged when the flag is off.
"""

import os
import re

from shared.academics import canonical
from shared.db import queries

_TRUTHY = {"1", "true", "yes", "y", "on"}
_DASHBOARD_PATH_RE = re.compile(r"^/dashboard/(\d+)(?:/|$)")


def is_demo_auth_enabled():
    return os.environ.get("DEMO_AUTH_ENABLED", "").strip().lower() in _TRUTHY


def _connect():
    return queries.connect_auth_db()


def _set_demo_student_session(session, *, enrollment_id, school_code=""):
    normalized_school_code = canonical.normalize_school_code(school_code)

    with _connect() as conn:
        queries.create_tables(conn)
        mapping = queries.get_students_sheet_map_row(
            conn,
            int(enrollment_id),
            school_key=normalized_school_code,
        )
        if not mapping and not normalized_school_code:
            mapping = queries.get_students_sheet_map_row(conn, int(enrollment_id))
        if not mapping:
            return False

        student_row_id = int(mapping["student_row_id"])
        student = queries.get_student_admin_row(conn, student_row_id)
        if not student:
            return False

    session.clear()
    session["auth_role"] = "student"
    session["auth_login"] = str(student["student_id"] or "").strip()
    session["student_db_id"] = student_row_id
    session["student_id"] = str(student["student_id"] or "").strip()
    session["student_enrollment_id"] = int(enrollment_id)
    session["student_full_name"] = str(student["full_name"] or "").strip()
    if normalized_school_code:
        session["student_school_code"] = normalized_school_code
    session["demo_auth"] = True
    return True


def _set_demo_admin_session(session):
    login = os.environ.get("DEMO_ADMIN_LOGIN", "").strip()
    with _connect() as conn:
        queries.create_tables(conn)
        if login:
            row = queries.get_admin_credentials_row(conn, login)
        else:
            row = conn.execute(
                """
                SELECT id, login, password_hash, role, is_owner
                FROM admins
                WHERE lower(role) IN ('owner', 'admin', 'ceo', 'academic_director', 'customer_support', 'hr')
                ORDER BY is_owner DESC, id ASC
                LIMIT 1
                """
            ).fetchone()
        if not row:
            return False

    session.clear()
    session["auth_role"] = "admin"
    session["auth_login"] = str(row["login"] or "").strip()
    session["admin_id"] = int(row["id"])
    session["admin_role"] = str(row["role"] or "admin").strip().lower() or "admin"
    session["admin_is_owner"] = bool(row["is_owner"])
    session["admin_last_panel"] = "overview"
    session["admin_last_school"] = "all"
    session["demo_auth"] = True
    return True


def maybe_apply_demo_auth(request_obj):
    if not is_demo_auth_enabled():
        return False

    session = request_obj.session
    if session.get("auth_role"):
        return False

    path = request_obj.url.path
    dashboard_match = _DASHBOARD_PATH_RE.match(path)
    if dashboard_match:
        return _set_demo_student_session(
            session,
            enrollment_id=int(dashboard_match.group(1)),
            school_code=request_obj.query_params.get("school", ""),
        )

    if path == "/" or path == "/admin" or path.startswith("/admin/"):
        return _set_demo_admin_session(session)

    return False


__all__ = ["is_demo_auth_enabled", "maybe_apply_demo_auth"]
