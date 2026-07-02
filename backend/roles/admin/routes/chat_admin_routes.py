"""
Admin chat moderation API.

  GET    /admin/api/chat/messages?room=...&before_id=...   list messages (incl. deleted)
  DELETE /admin/api/chat/messages/<id>                     soft-delete any message
  POST   /admin/api/chat/block                             block a student
  DELETE /admin/api/chat/block/<student_id>               unblock a student
  GET    /admin/api/chat/blocked                           list blocked students
  GET    /admin/api/chat/rooms                             list distinct active rooms
"""

from backend.utils.response_helpers import jsonify
from backend.utils.context import request
from backend.domains.communication.chat_service import _DB_LOCK, connect_chat_db, fmt_display, utc_now_iso
from backend.utils.session import (
    current_auth_login,
    current_auth_role,
)
from database import queries
from pydantic import BaseModel

_PAGE_SIZE = 60


class AdminChatBlockPayload(BaseModel):
    studentId: str = ""
    reason: str = ""


def _require_admin():
    if current_auth_role() != "admin":
        return jsonify({"error": "Admin access required."}, status_code=403)
    return None


def _serialize(row) -> dict:
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


def register_admin_chat_routes(router):

    # ── List messages (admin sees deleted too) ─────────────────────────────────
    @router.get("/admin/api/chat/messages")
    def admin_api_chat_list():
        err = _require_admin()
        if err:
            return err

        room = request.args.get("room", "global").strip()
        try:
            before_id = int(request.args.get("before_id", 0))
        except (TypeError, ValueError):
            before_id = 0

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
                    (room, before_id, _PAGE_SIZE),
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
                    (room, _PAGE_SIZE),
                ).fetchall()

        messages = [_serialize(r) for r in reversed(rows)]
        return jsonify({"messages": messages, "room": room})

    # ── Soft-delete any message ────────────────────────────────────────────────
    @router.delete("/admin/api/chat/messages/{msg_id}")
    def admin_api_chat_delete(msg_id: int):
        err = _require_admin()
        if err:
            return err

        with _DB_LOCK:
            with connect_chat_db() as conn:
                queries.ensure_chat_schema(conn)
                row = conn.execute(
                    "SELECT id FROM msi_v2.chat_messages WHERE id = %s", (msg_id,)
                ).fetchone()
                if not row:
                    return jsonify({"error": "Message not found."}, status_code=404)
                conn.execute(
                    "UPDATE msi_v2.chat_messages SET is_deleted = true WHERE id = %s", (msg_id,)
                )
                conn.commit()

        return jsonify({"deleted": True, "id": msg_id})

    # ── Block a student ────────────────────────────────────────────────────────
    @router.post("/admin/api/chat/block")
    def admin_api_chat_block(payload: AdminChatBlockPayload):
        err = _require_admin()
        if err:
            return err

        student_id = payload.studentId.strip().lower()
        reason = payload.reason.strip()[:300]

        if not student_id:
            return jsonify({"error": "studentId required."}, status_code=400)

        now = utc_now_iso()
        admin_login = current_auth_login()
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
                    (student_id, admin_login, now, reason),
                )
                conn.commit()

        return jsonify({"blocked": True, "studentId": student_id}, status_code=201)

    # ── Unblock a student ──────────────────────────────────────────────────────
    @router.delete("/admin/api/chat/block/{student_id}")
    def admin_api_chat_unblock(student_id: str):
        err = _require_admin()
        if err:
            return err

        with _DB_LOCK:
            with connect_chat_db() as conn:
                queries.ensure_chat_schema(conn)
                conn.execute(
                    "DELETE FROM msi_v2.chat_blocked_users WHERE student_id = %s",
                    (student_id.strip().lower(),),
                )
                conn.commit()

        return jsonify({"unblocked": True, "studentId": student_id})

    # ── List blocked students ──────────────────────────────────────────────────
    @router.get("/admin/api/chat/blocked")
    def admin_api_chat_blocked():
        err = _require_admin()
        if err:
            return err

        with connect_chat_db() as conn:
            queries.ensure_chat_schema(conn)
            rows = conn.execute(
                """
                SELECT student_id, blocked_by_staff_login AS blocked_by_admin, blocked_at, reason
                FROM msi_v2.chat_blocked_users
                ORDER BY blocked_at DESC
                """
            ).fetchall()

        blocked = [
            {
                "studentId": str(r["student_id"]),
                "blockedBy": str(r["blocked_by_admin"]),
                "blockedAt": fmt_display(str(r["blocked_at"])),
                "reason": str(r["reason"]),
            }
            for r in rows
        ]
        return jsonify({"blocked": blocked})

    # ── List distinct rooms that have messages ─────────────────────────────────
    @router.get("/admin/api/chat/rooms")
    def admin_api_chat_rooms():
        err = _require_admin()
        if err:
            return err

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

        rooms = [
            {"room": str(r["room"]), "total": int(r["total"]), "active": int(r["active"])}
            for r in rows
        ]
        return jsonify({"rooms": rooms})
