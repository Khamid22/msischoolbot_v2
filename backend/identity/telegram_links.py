"""Telegram account linking helpers."""

from database.academics import canonical
from database import queries
from backend.identity.common import DB_LOCK, connect, utc_now_iso
from backend.identity.storage import init_storage


def get_bot_users_count():
    init_storage()
    with connect() as conn:
        return queries.get_bot_users_count(conn)


def record_bot_user(telegram_user):
    if telegram_user is None:
        return

    user_id = getattr(telegram_user, "id", None)
    if not isinstance(user_id, int):
        return

    username = getattr(telegram_user, "username", None)
    first_name = getattr(telegram_user, "first_name", None)
    last_name = getattr(telegram_user, "last_name", None)

    init_storage()
    now = utc_now_iso()

    with DB_LOCK:
        with connect() as conn:
            queries.upsert_bot_user(
                conn,
                user_id,
                username,
                first_name,
                last_name,
                now,
            )
            conn.commit()


def link_student_telegram_user(student_row_id, telegram_user_id):
    if not isinstance(student_row_id, int) or student_row_id <= 0:
        return False
    if not isinstance(telegram_user_id, int) or telegram_user_id <= 0:
        return False

    init_storage()

    with DB_LOCK:
        with connect() as conn:
            student_exists = queries.get_student_admin_row(conn, student_row_id)
            if not student_exists:
                return False
            queries.clear_student_telegram_user_conflicts(
                conn,
                telegram_user_id,
                student_row_id,
            )
            queries.clear_admin_telegram_user_conflicts(conn, telegram_user_id)
            queries.clear_parent_telegram_user_conflicts(conn, telegram_user_id)
            queries.update_student_telegram_user(conn, telegram_user_id, student_row_id)
            conn.commit()
    return True


def link_admin_telegram_user(admin_id, telegram_user_id):
    if not isinstance(admin_id, int) or admin_id <= 0:
        return False
    if not isinstance(telegram_user_id, int) or telegram_user_id <= 0:
        return False

    init_storage()

    with DB_LOCK:
        with connect() as conn:
            admin_exists = queries.get_admin_row_by_id(conn, admin_id)
            if not admin_exists:
                return False
            queries.clear_student_telegram_user_conflicts(conn, telegram_user_id, -1)
            queries.clear_admin_telegram_user_conflicts(conn, telegram_user_id, admin_id)
            queries.clear_parent_telegram_user_conflicts(conn, telegram_user_id)
            queries.update_admin_telegram_user(conn, telegram_user_id, admin_id)
            conn.commit()
    return True


def get_admin_by_telegram_user_id(telegram_user_id):
    if not isinstance(telegram_user_id, int) or telegram_user_id <= 0:
        return None

    init_storage()
    with connect() as conn:
        row = queries.get_admin_by_telegram_id(conn, telegram_user_id)

    if not row:
        return None
    return {
        "id": int(row["id"]),
        "login": str(row["login"]),
        "role": str(row["role"]),
        "is_owner": bool(row["is_owner"]),
    }


def get_teacher_by_telegram_user_id(telegram_user_id):
    if not isinstance(telegram_user_id, int) or telegram_user_id <= 0:
        return None

    init_storage()
    with connect() as conn:
        row = queries.get_teacher_by_telegram_id(conn, telegram_user_id)

    if not row:
        return None
    try:
        teacher_id = int(row["id"])
    except (TypeError, ValueError):
        teacher_id = 0
    if teacher_id <= 0:
        return None
    return {
        "id": teacher_id,
        "staff_id": int(row["staff_id"] or 0),
        "full_name": str(row["full_name"]),
        "login": str(row["login"]),
        "assigned_group": str(row["assigned_group"] or "").strip(),
    }


def unlink_telegram_user_links(telegram_user_id):
    if not isinstance(telegram_user_id, int) or telegram_user_id <= 0:
        return {
            "success": False,
            "had_student_link": False,
            "had_admin_link": False,
            "had_parent_link": False,
        }

    init_storage()
    with DB_LOCK:
        with connect() as conn:
            student_row = queries.get_student_by_telegram_id(conn, telegram_user_id)
            admin_row = queries.get_admin_by_telegram_id(conn, telegram_user_id)
            parent_row = queries.get_parent_by_telegram_id(conn, telegram_user_id)

            queries.clear_student_telegram_user_conflicts(conn, telegram_user_id, -1)
            queries.clear_admin_telegram_user_conflicts(conn, telegram_user_id)
            queries.clear_parent_telegram_user_conflicts(conn, telegram_user_id)
            conn.commit()

    return {
        "success": True,
        "had_student_link": bool(student_row),
        "had_admin_link": bool(admin_row),
        "had_parent_link": bool(parent_row),
    }


def unlink_student_telegram_user(student_row_id):
    if not isinstance(student_row_id, int) or student_row_id <= 0:
        return False

    init_storage()
    with DB_LOCK:
        with connect() as conn:
            student_exists = queries.get_student_admin_row(conn, student_row_id)
            if not student_exists:
                return False
            queries.update_student_telegram_user(conn, None, student_row_id)
            conn.commit()
    return True


def get_student_by_telegram_user_id(telegram_user_id):
    if not isinstance(telegram_user_id, int) or telegram_user_id <= 0:
        return None

    init_storage()
    with connect() as conn:
        row = queries.get_student_by_telegram_id(conn, telegram_user_id)

    if not row:
        return None
    enrollment_id = row["enrollment_id"]
    return {
        "id": int(row["id"]),
        "full_name": str(row["full_name"]),
        "student_id": str(row["student_id"]),
        "subjects": str(row["subjects"]),
        "school_code": canonical.normalize_school_code(row["school_key"]),
        "enrollment_id": int(enrollment_id) if enrollment_id is not None else None,
    }


__all__ = [
    "get_admin_by_telegram_user_id",
    "get_bot_users_count",
    "get_student_by_telegram_user_id",
    "get_teacher_by_telegram_user_id",
    "link_admin_telegram_user",
    "link_student_telegram_user",
    "record_bot_user",
    "unlink_student_telegram_user",
    "unlink_telegram_user_links",
]
