"""Centralized session/auth state helpers used by route modules."""

from flask import session, url_for
from flask_login import current_user, login_user, logout_user

from web.backend.auth.session import build_admin_user, build_student_user

from web.backend.utils.normalization import normalize_school_code


def current_auth_role():
    role = str(session.get("auth_role", "")).strip().lower()
    if role in {"admin", "student"}:
        return role

    if bool(getattr(current_user, "is_authenticated", False)):
        role = str(getattr(current_user, "role", "")).strip().lower()
        if role in {"admin", "student"}:
            return role

    return ""


def current_auth_login():
    auth_login = str(session.get("auth_login", "")).strip()
    if auth_login:
        return auth_login

    if bool(getattr(current_user, "is_authenticated", False)):
        auth_login = str(getattr(current_user, "auth_login", "")).strip()
        if auth_login:
            return auth_login
    return ""


def current_student_enrollment_id():
    if current_auth_role() != "student":
        return None

    raw_value = session.get("student_enrollment_id")
    try:
        parsed_value = int(raw_value)
    except (TypeError, ValueError):
        parsed_value = None
    if parsed_value and parsed_value > 0:
        return parsed_value

    return None


def current_student_db_id():
    if current_auth_role() != "student":
        return None

    raw_value = session.get("student_db_id")
    try:
        parsed_value = int(raw_value)
    except (TypeError, ValueError):
        parsed_value = None
    if parsed_value and parsed_value > 0:
        return parsed_value

    if bool(getattr(current_user, "is_authenticated", False)) and str(
        getattr(current_user, "role", "")
    ).strip().lower() == "student":
        raw_user_value = getattr(current_user, "user_id", None)
        try:
            parsed_user_value = int(raw_user_value)
        except (TypeError, ValueError):
            parsed_user_value = None
        if parsed_user_value and parsed_user_value > 0:
            return parsed_user_value

    return None


def current_student_full_name():
    if current_auth_role() != "student":
        return ""

    current_name = str(session.get("student_full_name", "")).strip()
    if current_name:
        return current_name

    if bool(getattr(current_user, "is_authenticated", False)) and str(
        getattr(current_user, "role", "")
    ).strip().lower() == "student":
        current_name = str(getattr(current_user, "student_full_name", "")).strip()
        if current_name:
            return current_name
    return ""


def current_student_school_code():
    if current_auth_role() != "student":
        return ""

    session_school_code = normalize_school_code(session.get("student_school_code", ""))
    if session_school_code:
        return session_school_code

    if bool(getattr(current_user, "is_authenticated", False)) and str(
        getattr(current_user, "role", "")
    ).strip().lower() == "student":
        school_code = normalize_school_code(getattr(current_user, "student_school_code", ""))
        if school_code:
            return school_code

    return ""


def parse_telegram_user_id(raw_value):
    try:
        parsed = int(str(raw_value).strip())
    except (TypeError, ValueError):
        return None
    if parsed <= 0:
        return None
    return parsed


def current_admin_role():
    """Returns the admin's specific role: 'owner', 'admin', 'parent', or ''."""
    if current_auth_role() != "admin":
        return ""
    return str(session.get("admin_role", "admin")).strip().lower()


def set_admin_session(admin):
    portal_user = build_admin_user(admin)
    if portal_user is None:
        return False

    admin_role = str(admin.get("role", "admin")).strip().lower() or "admin"
    session.clear()
    login_user(portal_user, remember=False)
    session["auth_role"] = "admin"
    session["auth_login"] = str(admin.get("login", "")).strip()
    session["admin_id"] = int(admin["id"])
    session["admin_role"] = admin_role
    session["admin_is_owner"] = bool(admin.get("is_owner"))
    session["admin_last_panel"] = "overview"
    session["admin_last_school"] = "all"
    session.permanent = True
    return True


def set_student_session(student, telegram_user_id=None):
    portal_user = build_student_user(student)
    if portal_user is None:
        return False

    try:
        student_db_id = int(student["id"])
    except (KeyError, TypeError, ValueError):
        return False

    if student_db_id <= 0:
        return False

    try:
        enrollment_id = int(student["enrollment_id"])
        if enrollment_id <= 0:
            enrollment_id = None
    except (KeyError, TypeError, ValueError):
        enrollment_id = None

    session.clear()
    login_user(portal_user, remember=False)
    session["auth_role"] = "student"
    session["auth_login"] = str(student.get("student_id", "")).strip()
    session["student_db_id"] = student_db_id
    session["student_id"] = str(student.get("student_id", "")).strip()
    if enrollment_id is not None:
        session["student_enrollment_id"] = enrollment_id
    session["student_full_name"] = str(student.get("full_name", "")).strip()
    student_school_code = normalize_school_code(student.get("school_code", ""))
    if student_school_code:
        session["student_school_code"] = student_school_code
    parsed_telegram_user_id = parse_telegram_user_id(telegram_user_id)
    if parsed_telegram_user_id is not None:
        session["telegram_user_id"] = parsed_telegram_user_id
    else:
        session.pop("telegram_user_id", None)
    session.permanent = True
    return True


def try_auto_login_student_by_telegram(telegram_user_id, fetch_student_by_telegram):
    if not isinstance(telegram_user_id, int) or telegram_user_id <= 0:
        return False

    student = fetch_student_by_telegram(telegram_user_id)
    if not student:
        return False
    return set_student_session(student, telegram_user_id)


def build_dashboard_url(enrollment_id, subject="", group="", **extra_params):
    route_params = {
        "student_id": int(enrollment_id),
    }
    normalized_subject = str(subject or "").strip()
    normalized_group = str(group or "").strip()
    normalized_school = normalize_school_code(extra_params.pop("school", ""))
    if not normalized_school:
        normalized_school = current_student_school_code()

    if normalized_subject:
        route_params["subject"] = normalized_subject
    if normalized_group:
        route_params["group"] = normalized_group
    if normalized_school:
        route_params["school"] = normalized_school
    for key, value in extra_params.items():
        if str(value or "").strip():
            route_params[key] = str(value).strip()
    return url_for("student.dashboard", **route_params)


def logout_portal_session():
    logout_user()
    session.clear()


__all__ = [
    "current_auth_role",
    "current_admin_role",
    "current_auth_login",
    "current_student_enrollment_id",
    "current_student_db_id",
    "current_student_full_name",
    "current_student_school_code",
    "parse_telegram_user_id",
    "set_admin_session",
    "set_student_session",
    "try_auto_login_student_by_telegram",
    "build_dashboard_url",
    "logout_portal_session",
]
