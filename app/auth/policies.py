def normalize_auth_role(role):
    normalized = str(role or "").strip().casefold()
    if normalized in {"admin", "student"}:
        return normalized
    return ""


def is_admin_role(role):
    return normalize_auth_role(role) == "admin"


def is_student_role(role):
    return normalize_auth_role(role) == "student"


def is_authenticated_session(session):
    auth_role = normalize_auth_role(session.get("auth_role", ""))
    if auth_role == "admin":
        return bool(session.get("admin_id"))
    if auth_role == "student":
        return bool(session.get("student_db_id")) and bool(session.get("student_sheet_id"))
    return False


__all__ = [
    "normalize_auth_role",
    "is_admin_role",
    "is_student_role",
    "is_authenticated_session",
]
