import threading
from datetime import datetime, timezone

from database import queries

_DB_LOCK = threading.Lock()


def connect_chat_db():
    return queries.connect_auth_db()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fmt_display(iso_str: str) -> str:
    """Return a human-readable timestamp like '10 Apr 2026, 14:32'."""
    try:
        dt = datetime.strptime(iso_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        return dt.strftime("%-d %b %Y, %H:%M")
    except Exception:
        return iso_str


PAGE_SIZE = 40
MAX_BODY = 800


def validate_room(room: str) -> bool:
    if not room:
        return False
    return room == "global" or room.startswith("subject:") or room.startswith("group:")


def is_blocked(conn, student_login: str) -> bool:
    queries.ensure_chat_schema(conn)
    row = conn.execute(
        "SELECT 1 FROM msi_v2.chat_blocked_users WHERE student_id = %s",
        (student_login.strip().lower(),),
    ).fetchone()
    return row is not None


def serialize_message(row) -> dict:
    return {
        "id": int(row["id"]),
        "room": str(row["room"]),
        "authorName": str(row["author_name"]),
        "authorStudentId": str(row["author_student_id"]),
        "body": str(row["body"]),
        "editedAt": fmt_display(str(row["edited_at"])) if row["edited_at"] else None,
        "createdAt": fmt_display(str(row["created_at"])),
        "createdAtRaw": str(row["created_at"]),
    }


def list_messages(room: str, *, before_id: int = 0, after_id: int = 0) -> list[dict]:
    with connect_chat_db() as conn:
        queries.ensure_chat_schema(conn)
        if after_id > 0:
            rows = conn.execute(
                """
                SELECT id, room, author_name, author_student_id, body,
                       edited_at, created_at
                FROM msi_v2.chat_messages
                WHERE room = %s AND is_deleted IS FALSE AND id > %s
                ORDER BY id ASC
                LIMIT %s
                """,
                (room, after_id, PAGE_SIZE),
            ).fetchall()
            return [serialize_message(r) for r in rows]

        if before_id > 0:
            rows = conn.execute(
                """
                SELECT id, room, author_name, author_student_id, body,
                       edited_at, created_at
                FROM msi_v2.chat_messages
                WHERE room = %s AND is_deleted IS FALSE AND id < %s
                ORDER BY id DESC
                LIMIT %s
                """,
                (room, before_id, PAGE_SIZE),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, room, author_name, author_student_id, body,
                       edited_at, created_at
                FROM msi_v2.chat_messages
                WHERE room = %s AND is_deleted IS FALSE
                ORDER BY id DESC
                LIMIT %s
                """,
                (room, PAGE_SIZE),
            ).fetchall()
    return [serialize_message(r) for r in reversed(rows)]


def send_message(*, room: str, author_name: str, student_login: str, body: str) -> dict:
    """Insert a chat message. Raises PermissionError when the author is blocked."""
    now = utc_now_iso()
    with _DB_LOCK:
        with connect_chat_db() as conn:
            queries.ensure_chat_schema(conn)
            if is_blocked(conn, student_login):
                raise PermissionError("You have been blocked from the chat.")

            inserted = conn.execute(
                """
                INSERT INTO msi_v2.chat_messages
                    (room, author_name, author_student_id, body, created_at)
                VALUES (%s, %s, %s, %s, %s::timestamptz)
                RETURNING id
                """,
                (room, author_name, student_login, body, now),
            )
            inserted_row = inserted.fetchone()
            msg_id = int(inserted_row["id"] or 0) if inserted_row else 0
            conn.commit()

    return {
        "id": msg_id,
        "room": room,
        "authorName": author_name,
        "authorStudentId": student_login,
        "body": body,
        "editedAt": None,
        "createdAt": fmt_display(now),
        "createdAtRaw": now,
    }


def _own_message_row(conn, msg_id: int, student_login: str):
    queries.ensure_chat_schema(conn)
    row = conn.execute(
        "SELECT author_student_id FROM msi_v2.chat_messages WHERE id = %s AND is_deleted IS FALSE",
        (msg_id,),
    ).fetchone()
    if not row:
        raise LookupError("Message not found.")
    if str(row["author_student_id"]).strip().lower() != student_login.strip().lower():
        raise PermissionError("You can only edit your own messages.")


def edit_message(msg_id: int, *, student_login: str, body: str) -> dict:
    now = utc_now_iso()
    with _DB_LOCK:
        with connect_chat_db() as conn:
            _own_message_row(conn, msg_id, student_login)
            conn.execute(
                "UPDATE msi_v2.chat_messages SET body = %s, edited_at = %s::timestamptz WHERE id = %s",
                (body, now, msg_id),
            )
            conn.commit()
    return {"id": msg_id, "body": body, "editedAt": fmt_display(now)}


def delete_message(msg_id: int, *, student_login: str) -> None:
    with _DB_LOCK:
        with connect_chat_db() as conn:
            try:
                _own_message_row(conn, msg_id, student_login)
            except PermissionError:
                raise PermissionError("You can only delete your own messages.")
            conn.execute(
                "UPDATE msi_v2.chat_messages SET is_deleted = TRUE WHERE id = %s",
                (msg_id,),
            )
            conn.commit()
