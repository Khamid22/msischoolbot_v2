"""Chat policy, validation, serialization, and transaction workflows."""

import threading
from datetime import datetime, timezone

from backend.modules.communication import repository

_DB_LOCK = threading.Lock()
PAGE_SIZE = 40
ADMIN_PAGE_SIZE = 60
MAX_BODY = 800


def connect_chat_db():
    return repository.connect()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fmt_display(iso_str: str) -> str:
    try:
        parsed = datetime.fromisoformat(str(iso_str).replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc).strftime("%-d %b %Y, %H:%M")
    except (TypeError, ValueError):
        return str(iso_str)


def validate_room(room: str) -> bool:
    normalized = str(room or "").strip()
    if not normalized or len(normalized) > 160:
        return False
    if normalized == "global":
        return True
    prefix, separator, value = normalized.partition(":")
    return bool(separator and prefix in {"subject", "group"} and value.strip())


def student_can_access_room(student_db_id: int, room: str) -> bool:
    if not validate_room(room):
        return False
    if room == "global":
        return True
    try:
        student_id = int(student_db_id)
    except (TypeError, ValueError):
        return False
    if student_id <= 0:
        return False
    room_type, _, room_value = room.partition(":")
    with connect_chat_db() as conn:
        row = (
            repository.student_has_subject_room(conn, student_id, room_value)
            if room_type == "subject"
            else repository.student_has_group_room(conn, student_id, room_value)
        )
    return row is not None


def serialize_message(row) -> dict:
    return {
        "id": int(row["id"]), "room": str(row["room"]),
        "authorName": str(row["author_name"]), "authorStudentId": str(row["author_student_id"]),
        "body": str(row["body"]),
        "editedAt": fmt_display(str(row["edited_at"])) if row["edited_at"] else None,
        "createdAt": fmt_display(str(row["created_at"])), "createdAtRaw": str(row["created_at"]),
    }


def list_messages(room: str, *, before_id=0, after_id=0) -> list[dict]:
    with connect_chat_db() as conn:
        rows = repository.list_message_rows(
            conn, room, before_id=before_id, after_id=after_id, limit=PAGE_SIZE
        )
    if after_id <= 0:
        rows = reversed(rows)
    return [serialize_message(row) for row in rows]


def send_message(*, room: str, author_name: str, student_login: str, body: str) -> dict:
    now = utc_now_iso()
    with _DB_LOCK, connect_chat_db() as conn:
        if repository.is_blocked(conn, student_login):
            raise PermissionError("You have been blocked from the chat.")
        inserted = repository.insert_message(
            conn, room=room, author_name=author_name, student_login=student_login,
            body=body, created_at=now,
        )
        conn.commit()
    message_id = int(inserted["id"] or 0) if inserted else 0
    return {"id": message_id, "room": room, "authorName": author_name,
            "authorStudentId": student_login, "body": body, "editedAt": None,
            "createdAt": fmt_display(now), "createdAtRaw": now}


def _require_owned_message(conn, message_id: int, student_login: str):
    row = repository.get_message_author(conn, message_id)
    if not row:
        raise LookupError("Message not found.")
    if str(row["author_student_id"]).strip().lower() != student_login.strip().lower():
        raise PermissionError("You can only edit your own messages.")


def edit_message(msg_id: int, *, student_login: str, body: str) -> dict:
    now = utc_now_iso()
    with _DB_LOCK, connect_chat_db() as conn:
        _require_owned_message(conn, msg_id, student_login)
        repository.update_message(conn, msg_id, body, now)
        conn.commit()
    return {"id": msg_id, "body": body, "editedAt": fmt_display(now)}


def delete_message(msg_id: int, *, student_login: str) -> None:
    with _DB_LOCK, connect_chat_db() as conn:
        try:
            _require_owned_message(conn, msg_id, student_login)
        except PermissionError as exc:
            raise PermissionError("You can only delete your own messages.") from exc
        repository.soft_delete_message(conn, msg_id)
        conn.commit()


def serialize_admin_message(row) -> dict:
    result = serialize_message(row)
    result["isDeleted"] = bool(row["is_deleted"])
    result.pop("createdAtRaw", None)
    return result


def admin_list_messages(room: str, *, before_id=0) -> list[dict]:
    with connect_chat_db() as conn:
        rows = repository.list_message_rows(
            conn, room, before_id=before_id, limit=ADMIN_PAGE_SIZE, include_deleted=True
        )
    return [serialize_admin_message(row) for row in reversed(rows)]


def admin_delete_message(msg_id: int) -> None:
    with _DB_LOCK, connect_chat_db() as conn:
        if not repository.message_exists(conn, msg_id):
            raise LookupError("Message not found.")
        repository.soft_delete_message(conn, msg_id)
        conn.commit()


def block_student(student_id: str, *, blocked_by: str, reason: str) -> None:
    with _DB_LOCK, connect_chat_db() as conn:
        repository.upsert_blocked_student(
            conn, student_id=student_id, blocked_by=blocked_by,
            blocked_at=utc_now_iso(), reason=reason,
        )
        conn.commit()


def unblock_student(student_id: str) -> None:
    with _DB_LOCK, connect_chat_db() as conn:
        repository.delete_blocked_student(conn, student_id)
        conn.commit()


def list_blocked_students() -> list[dict]:
    with connect_chat_db() as conn:
        rows = repository.list_blocked_student_rows(conn)
    return [{"studentId": str(row["student_id"]), "blockedBy": str(row["blocked_by_admin"]),
             "blockedAt": fmt_display(str(row["blocked_at"])), "reason": str(row["reason"])}
            for row in rows]


def list_rooms() -> list[dict]:
    with connect_chat_db() as conn:
        rows = repository.list_room_rows(conn)
    return [{"room": str(row["room"]), "total": int(row["total"]), "active": int(row["active"])}
            for row in rows]
