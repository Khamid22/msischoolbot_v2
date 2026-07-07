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


# ── Admin moderation ─────────────────────────────────────────────────────────

ADMIN_PAGE_SIZE = 60


def serialize_admin_message(row) -> dict:
    return {
        "id": int(row["id"]),
        "room": str(row["room"]),
        "authorName": str(row["author_name"]),
        "authorStudentId": str(row["author_student_id"]),
        "body": str(row["body"]),
        "isDeleted": bool(row["is_deleted"]),
        "editedAt": fmt_display(str(row["edited_at"])) if row["edited_at"] else None,
        "createdAt": fmt_display(str(row["created_at"])),
    }


def admin_list_messages(room: str, *, before_id: int = 0) -> list[dict]:
    """List messages for moderation — includes soft-deleted ones."""
    with connect_chat_db() as conn:
        queries.ensure_chat_schema(conn)
        if before_id > 0:
            rows = conn.execute(
                """
                SELECT id, room, author_name, author_student_id, body,
                       is_deleted, edited_at, created_at
                FROM msi_v2.chat_messages
                WHERE room = %s AND id < %s
                ORDER BY id DESC LIMIT %s
                """,
                (room, before_id, ADMIN_PAGE_SIZE),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, room, author_name, author_student_id, body,
                       is_deleted, edited_at, created_at
                FROM msi_v2.chat_messages
                WHERE room = %s
                ORDER BY id DESC LIMIT %s
                """,
                (room, ADMIN_PAGE_SIZE),
            ).fetchall()
    return [serialize_admin_message(r) for r in reversed(rows)]


def admin_delete_message(msg_id: int) -> None:
    with _DB_LOCK:
        with connect_chat_db() as conn:
            queries.ensure_chat_schema(conn)
            row = conn.execute(
                "SELECT id FROM msi_v2.chat_messages WHERE id = %s", (msg_id,)
            ).fetchone()
            if not row:
                raise LookupError("Message not found.")
            conn.execute(
                "UPDATE msi_v2.chat_messages SET is_deleted = true WHERE id = %s", (msg_id,)
            )
            conn.commit()


def block_student(student_id: str, *, blocked_by: str, reason: str) -> None:
    now = utc_now_iso()
    with _DB_LOCK:
        with connect_chat_db() as conn:
            queries.ensure_chat_schema(conn)
            conn.execute(
                """
                INSERT INTO msi_v2.chat_blocked_users (student_id, blocked_by_staff_login, blocked_at, reason)
                VALUES (%s, %s, %s::timestamptz, %s)
                ON CONFLICT(student_id) DO UPDATE SET
                    blocked_by_staff_login = excluded.blocked_by_staff_login,
                    blocked_at = excluded.blocked_at,
                    reason = excluded.reason
                """,
                (student_id, blocked_by, now, reason),
            )
            conn.commit()


def unblock_student(student_id: str) -> None:
    with _DB_LOCK:
        with connect_chat_db() as conn:
            queries.ensure_chat_schema(conn)
            conn.execute(
                "DELETE FROM msi_v2.chat_blocked_users WHERE student_id = %s",
                (student_id.strip().lower(),),
            )
            conn.commit()


def list_blocked_students() -> list[dict]:
    with connect_chat_db() as conn:
        queries.ensure_chat_schema(conn)
        rows = conn.execute(
            """
            SELECT student_id, blocked_by_staff_login AS blocked_by_admin, blocked_at, reason
            FROM msi_v2.chat_blocked_users
            ORDER BY blocked_at DESC
            """
        ).fetchall()
    return [
        {
            "studentId": str(r["student_id"]),
            "blockedBy": str(r["blocked_by_admin"]),
            "blockedAt": fmt_display(str(r["blocked_at"])),
            "reason": str(r["reason"]),
        }
        for r in rows
    ]


def list_rooms() -> list[dict]:
    with connect_chat_db() as conn:
        queries.ensure_chat_schema(conn)
        rows = conn.execute(
            """
            SELECT room, COUNT(*) as total,
                   SUM(CASE WHEN is_deleted IS FALSE THEN 1 ELSE 0 END) as active
            FROM msi_v2.chat_messages
            GROUP BY room
            ORDER BY MAX(id) DESC
            """
        ).fetchall()
    return [
        {"room": str(r["room"]), "total": int(r["total"]), "active": int(r["active"])}
        for r in rows
    ]
