"""Parent client account workflows shared by bot and web."""

from datetime import datetime

from database import queries


def _utc_now_iso():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def link_parent_via_invite(
    student_row_id,
    full_name,
    phone="",
    telegram_username="",
    telegram_user_id=None,
):
    """Create/update a parent CLIENT record and link it to a student."""
    now = _utc_now_iso()
    with queries.connect_auth_db() as conn:
        parent = queries.link_parent_from_invite(
            conn,
            student_row_id=int(student_row_id),
            full_name=full_name,
            phone=phone,
            telegram_username=telegram_username,
            telegram_user_id=telegram_user_id,
            now=now,
        )
        if parent and telegram_user_id:
            parsed_telegram_user_id = int(telegram_user_id)
            queries.clear_student_telegram_user_conflicts(conn, parsed_telegram_user_id, -1)
            queries.clear_admin_telegram_user_conflicts(conn, parsed_telegram_user_id)
            queries.clear_parent_telegram_user_conflicts(
                conn,
                parsed_telegram_user_id,
                int(parent["id"]),
            )
    return dict(parent) if parent else None


def parent_from_telegram_user_id(telegram_user_id):
    try:
        parsed = int(telegram_user_id)
    except (TypeError, ValueError):
        return None
    if parsed <= 0:
        return None
    with queries.connect_auth_db() as conn:
        row = queries.get_parent_by_telegram_id(conn, parsed)
    return dict(row) if row else None


def parent_children(parent_id):
    try:
        parsed = int(parent_id)
    except (TypeError, ValueError):
        return []
    if parsed <= 0:
        return []
    with queries.connect_auth_db() as conn:
        rows = queries.list_parent_client_child_rows(conn, parsed)
    return [dict(row) for row in rows or []]


__all__ = [
    "link_parent_via_invite",
    "parent_children",
    "parent_from_telegram_user_id",
]
