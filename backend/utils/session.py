"""Centralized session/auth state helpers used by route modules."""

from backend.identity.roles import dashboard_path_for_role, is_valid_role, normalize_role
from backend.utils.context import session
from database.academics.canonical import normalize_school_code


def current_auth_role():
    role = normalize_role(session.get("auth_role", ""))
    if is_valid_role(role):
        return role
    return ""


def current_teacher_id():
    if current_auth_role() != "teacher":
        return None
    try:
        parsed_value = int(session.get("teacher_id"))
    except (TypeError, ValueError):
        return None
    return parsed_value if parsed_value > 0 else None


def current_teacher_staff_id():
    if current_auth_role() != "teacher":
        return None
    try:
        parsed_value = int(session.get("teacher_staff_id"))
    except (TypeError, ValueError):
        return None
    return parsed_value if parsed_value > 0 else None


def current_teacher_full_name():
    if current_auth_role() != "teacher":
        return ""
    return str(session.get("teacher_full_name", "")).strip()


def current_teacher_group():
    if current_auth_role() != "teacher":
        return ""
    return str(session.get("teacher_group", "")).strip()


def current_auth_login():
    return str(session.get("auth_login", "")).strip()


def current_parent_id():
    if current_auth_role() != "parent":
        return None
    try:
        parsed_value = int(session.get("parent_id"))
    except (TypeError, ValueError):
        return None
    return parsed_value if parsed_value > 0 else None


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

    return None


def current_student_full_name():
    if current_auth_role() != "student":
        return ""
    return str(session.get("student_full_name", "")).strip()


def current_student_school_code():
    if current_auth_role() != "student":
        return ""
    return normalize_school_code(session.get("student_school_code", ""), default="")


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


def current_staff_id():
    try:
        parsed_value = int(session.get("staff_id"))
    except (TypeError, ValueError):
        return None
    return parsed_value if parsed_value > 0 else None


def set_admin_session(admin):
    if not isinstance(admin, dict) or not admin.get("id"):
        return False

    raw_admin_role = str(admin.get("role", "admin")).strip() or "admin"
    portal_role = normalize_role(raw_admin_role) or "admin"
    if portal_role not in {
        "admin",
        "ceo",
        "hr_manager",
        "customer_support",
        "parent",
        "academic_director",
        "head_of_department",
    }:
        portal_role = "admin"
    admin_role = "owner" if raw_admin_role.strip().casefold() == "owner" else portal_role

    session.clear()
    session["auth_role"] = portal_role
    session["auth_login"] = str(admin.get("login", "")).strip()
    session["staff_id"] = int(admin["id"])
    session["staff_role"] = portal_role
    if portal_role == "admin":
        session["admin_id"] = int(admin["id"])
        session["admin_role"] = admin_role
        session["admin_is_owner"] = admin_role == "owner" or bool(admin.get("is_owner"))
        session["admin_last_panel"] = "overview"
        session["admin_last_school"] = "all"
    elif portal_role == "parent":
        # Legacy parent-client accounts can live in msi_staff. Keep admin_id so
        # the existing parent page can resolve linked children during cutover.
        session["admin_id"] = int(admin["id"])
    session.permanent = True
    return True


def set_student_session(student, telegram_user_id=None):
    if not isinstance(student, dict) or not student.get("id"):
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
    session["auth_role"] = "student"
    session["auth_login"] = str(student.get("student_id", "")).strip()
    session["student_db_id"] = student_db_id
    session["student_id"] = str(student.get("student_id", "")).strip()
    if enrollment_id is not None:
        session["student_enrollment_id"] = enrollment_id
    session["student_full_name"] = str(student.get("full_name", "")).strip()
    student_school_code = normalize_school_code(student.get("school_code", ""), default="")
    if student_school_code:
        session["student_school_code"] = student_school_code
    parsed_telegram_user_id = parse_telegram_user_id(telegram_user_id)
    if parsed_telegram_user_id is not None:
        session["telegram_user_id"] = parsed_telegram_user_id
    else:
        session.pop("telegram_user_id", None)
    session.permanent = True
    return True


def set_teacher_session(teacher):
    if not isinstance(teacher, dict) or not teacher.get("id"):
        return False

    try:
        teacher_id = int(teacher["id"])
    except (KeyError, TypeError, ValueError):
        return False
    if teacher_id <= 0:
        return False

    session.clear()
    session["auth_role"] = "teacher"
    session["auth_login"] = str(teacher.get("login", "")).strip()
    session["teacher_id"] = teacher_id
    try:
        teacher_staff_id = int(teacher.get("staff_id") or 0)
    except (TypeError, ValueError):
        teacher_staff_id = 0
    if teacher_staff_id > 0:
        session["teacher_staff_id"] = teacher_staff_id
    session["teacher_full_name"] = str(teacher.get("full_name", "")).strip()
    session["teacher_group"] = str(teacher.get("assigned_group", "")).strip()
    session.permanent = True
    return True


def set_parent_session(parent, telegram_user_id=None):
    if not isinstance(parent, dict) or not parent.get("id"):
        return False

    try:
        parent_id = int(parent["id"])
    except (KeyError, TypeError, ValueError):
        return False
    if parent_id <= 0:
        return False

    session.clear()
    session["auth_role"] = "parent"
    session["auth_login"] = str(parent.get("full_name") or parent.get("telegram_username") or f"parent-{parent_id}").strip()
    session["parent_id"] = parent_id
    session["parent_full_name"] = str(parent.get("full_name", "")).strip()
    parsed_telegram_user_id = parse_telegram_user_id(
        telegram_user_id if telegram_user_id is not None else parent.get("telegram_user_id")
    )
    if parsed_telegram_user_id is not None:
        session["telegram_user_id"] = parsed_telegram_user_id
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
    normalized_subject = str(subject or "").strip()
    normalized_group = str(group or "").strip()
    normalized_school = normalize_school_code(extra_params.pop("school", ""), default="")
    if not normalized_school:
        normalized_school = current_student_school_code()

    query_params = []
    if normalized_subject:
        query_params.append(f"subject={normalized_subject}")
    if normalized_group:
        query_params.append(f"group={normalized_group}")
    if normalized_school:
        query_params.append(f"school={normalized_school}")
    for key, value in extra_params.items():
        if str(value or "").strip():
            query_params.append(f"{key}={str(value).strip()}")

    url = f"/dashboard/{int(enrollment_id)}"
    if query_params:
        url += "?" + "&".join(query_params)
    return url


def dashboard_url_for_current_session():
    role = current_auth_role()
    if role == "student":
        enrollment_id = current_student_enrollment_id()
        if enrollment_id is not None:
            return build_dashboard_url(enrollment_id)
    return dashboard_path_for_role(role)


def url_for(endpoint: str, **kwargs) -> str:
    endpoint_clean = endpoint.split(".")[-1] if "." in endpoint else endpoint

    if endpoint_clean == "home":
        params = []
        for k, v in kwargs.items():
            if k != "_external":
                params.append(f"{k}={v}")
        url = "/"
        if params:
            url += "?" + "&".join(params)
        return url

    if endpoint_clean in {"dashboard", "chat_room", "student_resources", "rating_board", "aap_lessons", "ar_lessons", "student_office_hours"}:
        student_id = kwargs.get("student_id")
        subject = kwargs.get("subject", "")
        group = kwargs.get("group", "")
        school = kwargs.get("school", "")

        path_map = {
            "dashboard": f"/dashboard/{student_id}",
            "chat_room": f"/dashboard/{student_id}/chat",
            "student_resources": f"/dashboard/{student_id}/resources",
            "rating_board": f"/dashboard/{student_id}/rating-board",
            "aap_lessons": f"/dashboard/{student_id}/aap-lessons",
            "ar_lessons": f"/dashboard/{student_id}/ar-lessons",
            "student_office_hours": f"/dashboard/{student_id}/office-hours",
        }
        url = path_map[endpoint_clean]
        
        query_params = []
        if subject:
            query_params.append(f"subject={subject}")
        if group:
            query_params.append(f"group={group}")
        if school:
            query_params.append(f"school={school}")
        for k, v in kwargs.items():
            if k not in {"student_id", "subject", "group", "school", "_external"}:
                if v:
                    query_params.append(f"{k}={v}")
        if query_params:
            url += "?" + "&".join(query_params)
        return url

    if endpoint_clean == "profile_change_password":
        return "/profile/password"

    if endpoint_clean == "admin_continue":
        handoff = kwargs.get("handoff", "")
        return f"/admin/continue?handoff={handoff}"

    if endpoint_clean == "login":
        return "/login"

    if endpoint_clean == "logout":
        return "/logout"

    if endpoint_clean == "search_student_form":
        return "/search"

    if endpoint_clean == "save_admin_student_profile":
        s_id = kwargs.get("student_row_id")
        return f"/admin/students/{s_id}/profile"

    if endpoint_clean == "admin_change_student_password_route":
        s_id = kwargs.get("student_row_id")
        return f"/admin/students/{s_id}/password"

    if endpoint_clean == "admin_student_dashboard":
        s_id = kwargs.get("student_row_id")
        return f"/admin/students/{s_id}/dashboard"

    raise ValueError(f"Unknown endpoint in url_for: {endpoint}")


def logout_portal_session():
    session.clear()


__all__ = [
    "current_auth_role",
    "current_admin_role",
    "current_auth_login",
    "current_staff_id",
    "current_teacher_id",
    "current_teacher_staff_id",
    "current_teacher_full_name",
    "current_teacher_group",
    "current_parent_id",
    "current_student_enrollment_id",
    "current_student_db_id",
    "current_student_full_name",
    "current_student_school_code",
    "parse_telegram_user_id",
    "set_admin_session",
    "set_parent_session",
    "set_student_session",
    "try_auto_login_student_by_telegram",
    "build_dashboard_url",
    "dashboard_url_for_current_session",
    "url_for",
    "logout_portal_session",
]
