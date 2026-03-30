from flask_login import UserMixin

from app.auth.models import Admin, Student, StudentsSheetMap
from app.extensions import db


class PortalUser(UserMixin):
    def __init__(
        self,
        *,
        role,
        user_id,
        auth_login,
        is_owner=False,
        student_sheet_id=None,
        student_school_code="",
        student_full_name="",
    ):
        self.role = str(role or "").strip().lower()
        self.user_id = int(user_id)
        self.auth_login = str(auth_login or "").strip()
        self.is_owner = bool(is_owner)
        self.student_sheet_id = (
            int(student_sheet_id)
            if isinstance(student_sheet_id, int) and student_sheet_id > 0
            else None
        )
        self.student_school_code = str(student_school_code or "").strip().lower()
        self.student_full_name = str(student_full_name or "").strip()

    def get_id(self):
        return f"{self.role}:{self.user_id}"


def _normalize_school_code(value):
    normalized = str(value or "").strip().casefold()
    if normalized in {"school_5", "school-5", "school 5", "school5"}:
        return "school5"
    if normalized in {"sehriyo", "sehriyo school"}:
        return "sehriyo"
    return normalized


def build_admin_user(admin):
    if not isinstance(admin, dict):
        return None

    try:
        admin_id = int(admin["id"])
    except (KeyError, TypeError, ValueError):
        return None

    if admin_id <= 0:
        return None

    return PortalUser(
        role="admin",
        user_id=admin_id,
        auth_login=str(admin.get("login", "")).strip(),
        is_owner=bool(admin.get("is_owner")),
    )


def build_student_user(student):
    if not isinstance(student, dict):
        return None

    try:
        student_db_id = int(student["id"])
        sheet_student_id = int(student["sheet_student_id"])
    except (KeyError, TypeError, ValueError):
        return None

    if student_db_id <= 0 or sheet_student_id <= 0:
        return None

    return PortalUser(
        role="student",
        user_id=student_db_id,
        auth_login=str(student.get("student_id", "")).strip(),
        student_sheet_id=sheet_student_id,
        student_school_code=_normalize_school_code(student.get("school_code", "")),
        student_full_name=str(student.get("full_name", "")).strip(),
    )


def _parse_user_token(value):
    raw = str(value or "").strip()
    if not raw or ":" not in raw:
        return "", 0

    role, raw_id = raw.split(":", 1)
    role = str(role or "").strip().lower()
    if role not in {"admin", "student"}:
        return "", 0

    try:
        user_id = int(raw_id)
    except (TypeError, ValueError):
        return "", 0

    if user_id <= 0:
        return "", 0
    return role, user_id


def load_portal_user(user_token):
    role, user_id = _parse_user_token(user_token)
    if not role:
        return None

    if role == "admin":
        admin_row = db.session.get(Admin, user_id)
        if not admin_row:
            return None
        return PortalUser(
            role="admin",
            user_id=int(admin_row.id),
            auth_login=str(admin_row.login or "").strip(),
            is_owner=bool(admin_row.is_owner),
        )

    student_row = db.session.get(Student, user_id)
    if not student_row:
        return None

    sheet_map_row = (
        db.session.query(StudentsSheetMap)
        .filter(StudentsSheetMap.student_row_id == user_id)
        .first()
    )
    if not sheet_map_row or not int(sheet_map_row.sheet_student_id or 0):
        return None

    return PortalUser(
        role="student",
        user_id=int(student_row.id),
        auth_login=str(student_row.student_id or "").strip(),
        student_sheet_id=int(sheet_map_row.sheet_student_id),
        student_school_code=_normalize_school_code(student_row.school_key),
        student_full_name=str(student_row.full_name or "").strip(),
    )


def configure_login_manager(login_manager):
    login_manager.login_view = "student.home"
    login_manager.session_protection = "strong"

    @login_manager.user_loader
    def _load_user(user_token):
        return load_portal_user(user_token)


__all__ = [
    "PortalUser",
    "build_admin_user",
    "build_student_user",
    "load_portal_user",
    "configure_login_manager",
]
