"""
Admin chat moderation API.

  GET    /admin/api/chat/messages?room=...&before_id=...   list messages (incl. deleted)
  DELETE /admin/api/chat/messages/<id>                     soft-delete any message
  POST   /admin/api/chat/block                             block a student
  DELETE /admin/api/chat/block/<student_id>               unblock a student
  GET    /admin/api/chat/blocked                           list blocked students
  GET    /admin/api/chat/rooms                             list distinct active rooms
"""

from flask import jsonify, request

from web.backend.extensions import csrf
from web.backend.routes.chat import _DB_LOCK, connect_chat_db, fmt_display, utc_now_iso
from web.backend.admin.services.session_state_service import (
    current_auth_login,
    current_auth_role,
)

_PAGE_SIZE = 60


def _require_admin():
    if current_auth_role() != "admin":
        return jsonify({"error": "Admin access required."}), 403
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
    @csrf.exempt
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
            if before_id > 0:
                rows = conn.execute(
                    """
                    SELECT id, room, author_name, author_student_id, body,
                           is_deleted, edited_at, created_at
                    FROM chat_messages
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
                    FROM chat_messages
                    WHERE room = %s
                    ORDER BY id DESC LIMIT %s
                    """,
                    (room, _PAGE_SIZE),
                ).fetchall()

        messages = [_serialize(r) for r in reversed(rows)]
        return jsonify({"messages": messages, "room": room})

    # ── Soft-delete any message ────────────────────────────────────────────────
    @router.delete("/admin/api/chat/messages/<int:msg_id>")
    @csrf.exempt
    def admin_api_chat_delete(msg_id):
        err = _require_admin()
        if err:
            return err

        with _DB_LOCK:
            with connect_chat_db() as conn:
                row = conn.execute(
                    "SELECT id FROM chat_messages WHERE id = %s", (msg_id,)
                ).fetchone()
                if not row:
                    return jsonify({"error": "Message not found."}), 404
                conn.execute(
                    "UPDATE chat_messages SET is_deleted = 1 WHERE id = %s", (msg_id,)
                )
                conn.commit()

        return jsonify({"deleted": True, "id": msg_id})

    # ── Block a student ────────────────────────────────────────────────────────
    @router.post("/admin/api/chat/block")
    @csrf.exempt
    def admin_api_chat_block():
        err = _require_admin()
        if err:
            return err

        data = request.get_json(silent=True) or {}
        student_id = str(data.get("studentId", "")).strip().lower()
        reason = str(data.get("reason", "")).strip()[:300]

        if not student_id:
            return jsonify({"error": "studentId required."}), 400

        now = utc_now_iso()
        admin_login = current_auth_login()
        with _DB_LOCK:
            with connect_chat_db() as conn:
                conn.execute(
                    """
                    INSERT INTO chat_blocked_users (student_id, blocked_by_admin, blocked_at, reason)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT(student_id) DO UPDATE SET
                        blocked_by_admin = excluded.blocked_by_admin,
                        blocked_at = excluded.blocked_at,
                        reason = excluded.reason
                    """,
                    (student_id, admin_login, now, reason),
                )
                conn.commit()

        return jsonify({"blocked": True, "studentId": student_id}), 201

    # ── Unblock a student ──────────────────────────────────────────────────────
    @router.delete("/admin/api/chat/block/<student_id>")
    @csrf.exempt
    def admin_api_chat_unblock(student_id):
        err = _require_admin()
        if err:
            return err

        with _DB_LOCK:
            with connect_chat_db() as conn:
                conn.execute(
                    "DELETE FROM chat_blocked_users WHERE student_id = %s",
                    (student_id.strip().lower(),),
                )
                conn.commit()

        return jsonify({"unblocked": True, "studentId": student_id})

    # ── List blocked students ──────────────────────────────────────────────────
    @router.get("/admin/api/chat/blocked")
    @csrf.exempt
    def admin_api_chat_blocked():
        err = _require_admin()
        if err:
            return err

        with connect_chat_db() as conn:
            rows = conn.execute(
                """
                SELECT student_id, blocked_by_admin, blocked_at, reason
                FROM chat_blocked_users
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
    @csrf.exempt
    def admin_api_chat_rooms():
        err = _require_admin()
        if err:
            return err

        with connect_chat_db() as conn:
            rows = conn.execute(
                """
                SELECT room, COUNT(*) as total,
                       SUM(CASE WHEN is_deleted = 0 THEN 1 ELSE 0 END) as active
                FROM chat_messages
                GROUP BY room
                ORDER BY MAX(id) DESC
                """
            ).fetchall()

        rooms = [
            {"room": str(r["room"]), "total": int(r["total"]), "active": int(r["active"])}
            for r in rows
        ]
        return jsonify({"rooms": rooms})
