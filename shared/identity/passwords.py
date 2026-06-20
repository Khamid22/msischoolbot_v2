"""Student password change helpers."""

from werkzeug.security import check_password_hash, generate_password_hash

from shared.db import queries
from shared.identity.common import DB_LOCK, connect, utc_now_iso
from shared.identity.storage import init_storage


def change_student_password(student_row_id, current_password, new_password):
    if not isinstance(student_row_id, int) or student_row_id <= 0:
        return False, "Invalid student session."

    current_password_value = str(current_password or "")
    new_password_value = str(new_password or "")
    if not current_password_value:
        return False, "Current password is required."
    if not new_password_value:
        return False, "New password is required."
    if len(new_password_value) < 6:
        return False, "New password must be at least 6 characters."
    if current_password_value == new_password_value:
        return False, "New password must be different from current password."

    init_storage()
    with DB_LOCK:
        with connect() as conn:
            auth_row = queries.get_student_auth_row_by_id(conn, student_row_id)
            if not auth_row:
                return False, "Student account was not found."

            if not check_password_hash(
                str(auth_row["password_hash"] or ""),
                current_password_value,
            ):
                return False, "Current password is incorrect."

            queries.update_student_password(
                conn,
                student_row_id,
                new_password_value,
                generate_password_hash(new_password_value),
                utc_now_iso(),
            )
            conn.commit()

    return True, ""


def admin_change_student_password(student_row_id, new_password):
    if not isinstance(student_row_id, int) or student_row_id <= 0:
        return False, "Invalid student."

    new_password_value = str(new_password or "").strip()
    if not new_password_value:
        return False, "New password is required."
    if len(new_password_value) < 6:
        return False, "Password must be at least 6 characters."

    init_storage()
    with DB_LOCK:
        with connect() as conn:
            auth_row = queries.get_student_auth_row_by_id(conn, student_row_id)
            if not auth_row:
                return False, "Student account was not found."

            queries.update_student_password(
                conn,
                student_row_id,
                new_password_value,
                generate_password_hash(new_password_value),
                utc_now_iso(),
            )
            conn.commit()

    return True, ""


__all__ = ["admin_change_student_password", "change_student_password"]

