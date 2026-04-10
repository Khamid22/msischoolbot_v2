"""
Chat API routes for students.

Rooms:
  "global"           – school-wide chat
  "subject:<name>"   – e.g. "subject:Mathematics"
  "group:<name>"     – e.g. "group:Group A"

Endpoints:
  GET  /api/chat/messages?room=...&before_id=...   list messages (newest-first, 40 per page)
  POST /api/chat/messages                          send message
  PUT  /api/chat/messages/<id>                     edit own message
  DELETE /api/chat/messages/<id>                  soft-delete own message
"""

import threading
from datetime import datetime, timezone

from flask import jsonify, request

from app.extensions import csrf
from app.storage import queries
from app.routes.students.services.session_state_service import (
    current_auth_role,
    current_student_full_name,
)
from app.routes.admin.services.session_state_service import (
    current_auth_login as current_admin_login,
)

_DB_LOCK = threading.Lock()
_PAGE_SIZE = 40
_MAX_BODY = 800
_VALID_ROOM_PREFIXES = ("global", "subject:", "group:")


def _connect():
    return queries.connect_auth_db()


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fmt(iso_str):
    try:
        dt = datetime.strptime(iso_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        return dt.strftime("%-d %b %Y, %H:%M")
    except Exception:
        return iso_str


def _validate_room(room: str) -> bool:
    if not room:
        return False
    return any(room == "global" or room.startswith(p) for p in _VALID_ROOM_PREFIXES)


def _is_blocked(conn, student_login: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM chat_blocked_users WHERE student_id = ?",
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
        "editedAt": _fmt(str(row["edited_at"])) if row["edited_at"] else None,
        "createdAt": _fmt(str(row["created_at"])),
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

        with _connect() as conn:
            if before_id > 0:
                rows = conn.execute(
                    """
                    SELECT id, room, author_name, author_student_id, body,
                           edited_at, created_at
                    FROM chat_messages
                    WHERE room = ? AND is_deleted = 0 AND id < ?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (room, before_id, _PAGE_SIZE),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT id, room, author_name, author_student_id, body,
                           edited_at, created_at
                    FROM chat_messages
                    WHERE room = ? AND is_deleted = 0
                    ORDER BY id DESC
                    LIMIT ?
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

        # Use full_name as the stable login for blocking
        from app.routes.students.services.session_state_service import current_auth_login as _student_login
        student_login = _student_login() or author_name

        now = _now_iso()
        with _DB_LOCK:
            with _connect() as conn:
                if _is_blocked(conn, student_login):
                    return jsonify({"error": "You have been blocked from the chat."}), 403

                conn.execute(
                    """
                    INSERT INTO chat_messages
                        (room, author_name, author_student_id, body, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (room, author_name, student_login, body, now),
                )
                msg_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                conn.commit()

        return jsonify({
            "message": {
                "id": int(msg_id),
                "room": room,
                "authorName": author_name,
                "authorStudentId": student_login,
                "body": body,
                "editedAt": None,
                "createdAt": _fmt(now),
                "createdAtRaw": now,
            }
        }), 201

    # ── Edit own message ───────────────────────────────────────────────────────
    @students.put("/api/chat/messages/<int:msg_id>")
    @csrf.exempt
    def api_chat_edit(msg_id):
        if current_auth_role() != "student":
            return jsonify({"error": "Login required."}), 401

        from app.routes.students.services.session_state_service import current_auth_login as _student_login
        student_login = _student_login() or current_student_full_name()

        data = request.get_json(silent=True) or {}
        body = str(data.get("body", "")).strip()
        if not body:
            return jsonify({"error": "Message cannot be empty."}), 400
        if len(body) > _MAX_BODY:
            return jsonify({"error": f"Message too long (max {_MAX_BODY} chars)."}), 400

        now = _now_iso()
        with _DB_LOCK:
            with _connect() as conn:
                row = conn.execute(
                    "SELECT author_student_id FROM chat_messages WHERE id = ? AND is_deleted = 0",
                    (msg_id,),
                ).fetchone()
                if not row:
                    return jsonify({"error": "Message not found."}), 404
                if str(row["author_student_id"]).strip().lower() != student_login.strip().lower():
                    return jsonify({"error": "You can only edit your own messages."}), 403

                conn.execute(
                    "UPDATE chat_messages SET body = ?, edited_at = ? WHERE id = ?",
                    (body, now, msg_id),
                )
                conn.commit()

        return jsonify({"id": msg_id, "body": body, "editedAt": _fmt(now)})

    # ── Delete own message ─────────────────────────────────────────────────────
    @students.delete("/api/chat/messages/<int:msg_id>")
    @csrf.exempt
    def api_chat_delete(msg_id):
        if current_auth_role() != "student":
            return jsonify({"error": "Login required."}), 401

        from app.routes.students.services.session_state_service import current_auth_login as _student_login
        student_login = _student_login() or current_student_full_name()

        with _DB_LOCK:
            with _connect() as conn:
                row = conn.execute(
                    "SELECT author_student_id FROM chat_messages WHERE id = ? AND is_deleted = 0",
                    (msg_id,),
                ).fetchone()
                if not row:
                    return jsonify({"error": "Message not found."}), 404
                if str(row["author_student_id"]).strip().lower() != student_login.strip().lower():
                    return jsonify({"error": "You can only delete your own messages."}), 403

                conn.execute(
                    "UPDATE chat_messages SET is_deleted = 1 WHERE id = ?",
                    (msg_id,),
                )
                conn.commit()

        return jsonify({"deleted": True, "id": msg_id})
