"""
Chat API routes for students.

Rooms:
  "global"           – school-wide chat
  "subject:<name>"   – e.g. "subject:Mathematics"
  "group:<name>"     – e.g. "group:Group A"

Endpoints:
  GET    /api/chat/messages?room=...&before_id=...&after_id=...
                                                  list messages (newest-first, 40 per page)
  POST   /api/chat/messages                        send message
  PUT    /api/chat/messages/<id>                   edit own message
  DELETE /api/chat/messages/<id>                  soft-delete own message
"""

from web.backend.utils.response_helpers import jsonify, csrf
from web.backend.utils.context import request
from web.backend.domains.communication.chat_service import _DB_LOCK, connect_chat_db, fmt_display, utc_now_iso
from web.backend.utils.session import (
    current_auth_login,
    current_auth_role,
    current_student_full_name,
)
from shared.db import queries

_PAGE_SIZE = 40
_MAX_BODY = 800


def _validate_room(room: str) -> bool:
    if not room:
        return False
    return room == "global" or room.startswith("subject:") or room.startswith("group:")


def _is_blocked(conn, student_login: str) -> bool:
    queries.ensure_chat_schema(conn)
    row = conn.execute(
        "SELECT 1 FROM msi_v2.chat_blocked_users WHERE student_id = %s",
        (student_login.strip().lower(),),
    ).fetchone()
    return row is not None


def _serialize(row) -> dict:
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


def register_chat_routes(students):

    # ── List messages ──────────────────────────────────────────────────────────
    @students.get("/api/chat/messages")
    @csrf.exempt
    def api_chat_list():
        room = request.args.get("room", "global").strip()
        if not _validate_room(room):
            return jsonify({"error": "Invalid room."}), 400

        try:
            before_id = int(request.args.get("before_id", 0))
        except (TypeError, ValueError):
            before_id = 0
        try:
            after_id = int(request.args.get("after_id", 0))
        except (TypeError, ValueError):
            after_id = 0

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
                    (room, after_id, _PAGE_SIZE),
                ).fetchall()
                messages = [_serialize(r) for r in rows]
                return jsonify({"messages": messages, "room": room})

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
                    (room, before_id, _PAGE_SIZE),
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
                    (room, _PAGE_SIZE),
                ).fetchall()

        messages = [_serialize(r) for r in reversed(rows)]
        return jsonify({"messages": messages, "room": room})

    # ── Send message ───────────────────────────────────────────────────────────
    @students.post("/api/chat/messages")
    @csrf.exempt
    def api_chat_send():
        role = current_auth_role()
        if role != "student":
            return jsonify({"error": "Login required."}), 401

        author_name = current_student_full_name()
        if not author_name:
            return jsonify({"error": "Could not identify your account."}), 401

        data = request.get_json(silent=True) or {}
        room = str(data.get("room", "global")).strip()
        body = str(data.get("body", "")).strip()

        if not _validate_room(room):
            return jsonify({"error": "Invalid room."}), 400
        if not body:
            return jsonify({"error": "Message cannot be empty."}), 400
        if len(body) > _MAX_BODY:
            return jsonify({"error": f"Message too long (max {_MAX_BODY} chars)."}), 400

        student_login = current_auth_login() or author_name
        now = utc_now_iso()
        with _DB_LOCK:
            with connect_chat_db() as conn:
                queries.ensure_chat_schema(conn)
                if _is_blocked(conn, student_login):
                    return jsonify({"error": "You have been blocked from the chat."}), 403

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

        return jsonify({
            "message": {
                "id": msg_id,
                "room": room,
                "authorName": author_name,
                "authorStudentId": student_login,
                "body": body,
                "editedAt": None,
                "createdAt": fmt_display(now),
                "createdAtRaw": now,
            }
        }), 201

    # ── Edit own message ───────────────────────────────────────────────────────
    @students.put("/api/chat/messages/<int:msg_id>")
    @csrf.exempt
    def api_chat_edit(msg_id):
        if current_auth_role() != "student":
            return jsonify({"error": "Login required."}), 401

        student_login = current_auth_login() or current_student_full_name()

        data = request.get_json(silent=True) or {}
        body = str(data.get("body", "")).strip()
        if not body:
            return jsonify({"error": "Message cannot be empty."}), 400
        if len(body) > _MAX_BODY:
            return jsonify({"error": f"Message too long (max {_MAX_BODY} chars)."}), 400

        now = utc_now_iso()
        with _DB_LOCK:
            with connect_chat_db() as conn:
                queries.ensure_chat_schema(conn)
                row = conn.execute(
                    "SELECT author_student_id FROM msi_v2.chat_messages WHERE id = %s AND is_deleted IS FALSE",
                    (msg_id,),
                ).fetchone()
                if not row:
                    return jsonify({"error": "Message not found."}), 404
                if str(row["author_student_id"]).strip().lower() != student_login.strip().lower():
                    return jsonify({"error": "You can only edit your own messages."}), 403

                conn.execute(
                    "UPDATE msi_v2.chat_messages SET body = %s, edited_at = %s::timestamptz WHERE id = %s",
                    (body, now, msg_id),
                )
                conn.commit()

        return jsonify({"id": msg_id, "body": body, "editedAt": fmt_display(now)})

    # ── Soft-delete own message ────────────────────────────────────────────────
    @students.delete("/api/chat/messages/<int:msg_id>")
    @csrf.exempt
    def api_chat_delete(msg_id):
        if current_auth_role() != "student":
            return jsonify({"error": "Login required."}), 401

        student_login = current_auth_login() or current_student_full_name()

        with _DB_LOCK:
            with connect_chat_db() as conn:
                queries.ensure_chat_schema(conn)
                row = conn.execute(
                    "SELECT author_student_id FROM msi_v2.chat_messages WHERE id = %s AND is_deleted IS FALSE",
                    (msg_id,),
                ).fetchone()
                if not row:
                    return jsonify({"error": "Message not found."}), 404
                if str(row["author_student_id"]).strip().lower() != student_login.strip().lower():
                    return jsonify({"error": "You can only delete your own messages."}), 403

                conn.execute(
                    "UPDATE msi_v2.chat_messages SET is_deleted = true WHERE id = %s",
                    (msg_id,),
                )
                conn.commit()

        return jsonify({"deleted": True, "id": msg_id})
