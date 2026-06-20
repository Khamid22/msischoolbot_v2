from flask_login import UserMixin

from shared.academics import canonical
from shared.db import queries


class PortalUser(UserMixin):
    def __init__(
        self,
        *,
        role,
        user_id,
        auth_login,
        is_owner=False,
        student_school_code="",
        student_full_name="",
    ):
        self.role = str(role or "").strip().lower()
        self.user_id = int(user_id)
        self.auth_login = str(auth_login or "").strip()
        self.is_owner = bool(is_owner)
        self.student_school_code = str(student_school_code or "").strip().lower()
        self.student_full_name = str(student_full_name or "").strip()

    def get_id(self):
        return f"{self.role}:{self.user_id}"


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
    except (KeyError, TypeError, ValueError):
        return None

    if student_db_id <= 0:
        return None

    return PortalUser(
        role="student",
        user_id=student_db_id,
        auth_login=str(student.get("student_id", "")).strip(),
        student_school_code=canonical.normalize_school_code(student.get("school_code", ""), default=""),
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

    # Schema is created once at startup by shared.identity.account_service.init_storage(); this is a
    # hot per-request path (Flask-Login user loading), so do not run DDL here.
    with queries.connect_auth_db() as conn:

        if role == "admin":
            admin_row = conn.execute(
                """
                SELECT id, login, is_owner
                FROM admins
                WHERE id = %s
                """,
                (user_id,),
            ).fetchone()
            if not admin_row:
                return None
            return PortalUser(
                role="admin",
                user_id=int(admin_row["id"]),
                auth_login=str(admin_row["login"] or "").strip(),
                is_owner=bool(admin_row["is_owner"]),
            )

        student_row = conn.execute(
            """
            SELECT id, student_id, full_name, school_key
            FROM students
            WHERE id = %s
            """,
            (user_id,),
        ).fetchone()
        if not student_row:
            return None

        return PortalUser(
            role="student",
            user_id=int(student_row["id"]),
            auth_login=str(student_row["student_id"] or "").strip(),
            student_school_code=canonical.normalize_school_code(student_row["school_key"], default=""),
            student_full_name=str(student_row["full_name"] or "").strip(),
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
