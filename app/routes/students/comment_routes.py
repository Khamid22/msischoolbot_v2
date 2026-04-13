import threading
from datetime import datetime, timezone

from flask import jsonify, request

from app.extensions import csrf
from app.storage import queries
from app.routes.students.services.session_state_service import (
    current_auth_role,
    current_student_full_name,
)

_COMMENT_MAX_LENGTH = 500
_COMMENTS_PER_PAGE = 50
_DB_LOCK = threading.Lock()


def _connect():
    return queries.connect_auth_db()


def _utc_now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _format_display(iso_str):
    """Return a human-readable timestamp like '10 Apr 2026, 14:32'."""
    try:
        dt = datetime.strptime(iso_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        return dt.strftime("%-d %b %Y, %H:%M")
    except Exception:
        return iso_str


def register_comment_routes(students):
    @students.get("/api/resources/<int:resource_id>/comments")
    @csrf.exempt
    def api_list_comments(resource_id):
        with _connect() as conn:
            rows = conn.execute(
                """
                SELECT id, author_name, body, created_at
                FROM resource_comments
                WHERE resource_id = ?
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (resource_id, _COMMENTS_PER_PAGE),
            ).fetchall()
        comments = [
            {
                "id": int(row["id"]),
                "authorName": str(row["author_name"]),
                "body": str(row["body"]),
                "createdAt": _format_display(str(row["created_at"])),
            }
            for row in rows
        ]
        return jsonify({"comments": comments})

    @students.post("/api/resources/<int:resource_id>/comments")
    @csrf.exempt
    def api_post_comment(resource_id):
        if current_auth_role() != "student":
            return jsonify({"error": "Login required to leave a comment."}), 401

        author_name = current_student_full_name()
        if not author_name:
            return jsonify({"error": "Could not identify your account."}), 401

        data = request.get_json(silent=True) or {}
        body = str(data.get("body", "")).strip()
        if not body:
            return jsonify({"error": "Comment cannot be empty."}), 400
        if len(body) > _COMMENT_MAX_LENGTH:
            return jsonify({"error": f"Comment is too long (max {_COMMENT_MAX_LENGTH} characters)."}), 400

        now = _utc_now_iso()
        with _DB_LOCK:
            with _connect() as conn:
                # Verify resource exists
                exists = conn.execute(
                    "SELECT 1 FROM resources WHERE id = ? AND is_active = 1",
                    (resource_id,),
                ).fetchone()
                if not exists:
                    return jsonify({"error": "Resource not found."}), 404

                inserted = conn.execute(
                    """
                    INSERT INTO resource_comments (resource_id, author_name, body, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (resource_id, author_name, body, now),
                )
                comment_id = int(getattr(inserted, "lastrowid", 0) or 0)
                conn.commit()

        return jsonify({
            "comment": {
                "id": int(comment_id),
                "authorName": author_name,
                "body": body,
                "createdAt": _format_display(now),
            }
        }), 201
