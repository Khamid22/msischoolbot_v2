"""Login role detection and credential verification."""

import logging

from werkzeug.security import check_password_hash

from shared.academics import canonical
from shared.db import queries
from shared.identity.common import connect
from shared.identity.storage import init_storage

# ─────────────────────────────────────────────────────────────────────────────
# ⚠️  TEMPORARY DEV BYPASS — admin login accepts ANY password.
# Requested for local iPhone testing. MUST be reverted before production:
# set _ADMIN_PASSWORDLESS_LOGIN = False (or delete it and restore the password
# check in verify_admin_credentials below).
# ─────────────────────────────────────────────────────────────────────────────
_ADMIN_PASSWORDLESS_LOGIN = False


def detect_login_role(login):
    normalized = (login or "").strip().casefold()
    if normalized == "admin" or normalized.startswith("staff"):
        return "admin"
    if normalized.startswith("tch"):
        return "teacher"
    if normalized.startswith("msi"):
        return "student"
    return ""


def verify_admin_credentials(login, password):
    init_storage()
    with connect() as conn:
        row = queries.get_admin_credentials_row(
            conn,
            (login or "").strip(),
        )

    if not row:
        return None
    if _ADMIN_PASSWORDLESS_LOGIN:
        logging.warning(
            "ADMIN PASSWORDLESS LOGIN bypass active — accepting login '%s' without "
            "a password. Disable _ADMIN_PASSWORDLESS_LOGIN before production.",
            (login or "").strip(),
        )
    elif not check_password_hash(row["password_hash"], password or ""):
        return None

    # Disabled accounts (currently only parent client accounts can be disabled)
    # keep their data but are blocked from signing in.
    try:
        if int(row["disabled"] or 0) == 1:
            return None
    except (KeyError, IndexError, TypeError):
        pass

    return {
        "id": int(row["id"]),
        "login": str(row["login"]),
        "role": str(row["role"]),
        "is_owner": bool(row["is_owner"]),
    }


def verify_student_credentials(login, password):
    init_storage()
    student_login = (login or "").strip().upper()

    with connect() as conn:
        row = queries.get_student_login_row(conn, student_login)

    if not row:
        return None
    if not check_password_hash(row["password_hash"], password or ""):
        return None

    enrollment_id = row["enrollment_id"]
    return {
        "id": int(row["id"]),
        "full_name": str(row["full_name"]),
        "student_id": str(row["student_id"]),
        "subjects": str(row["subjects"]),
        "school_code": canonical.normalize_school_code(row["school_key"]),
        "telegram_user_id": (
            int(row["telegram_user_id"])
            if row["telegram_user_id"] is not None
            else None
        ),
        "enrollment_id": int(enrollment_id) if enrollment_id is not None else None,
    }


def verify_teacher_credentials(login, password):
    init_storage()
    teacher_login = (login or "").strip()

    with connect() as conn:
        row = queries.get_teacher_login_row(conn, teacher_login)

    if not row:
        return None
    if not check_password_hash(row["password_hash"], password or ""):
        return None

    return {
        "id": int(row["id"]),
        "full_name": str(row["full_name"]),
        "login": str(row["login"]),
        "assigned_group": str(row["assigned_group"] or "").strip(),
    }


__all__ = [
    "detect_login_role",
    "verify_admin_credentials",
    "verify_student_credentials",
    "verify_teacher_credentials",
]

