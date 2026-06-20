from web.backend.utils.response_helpers import jsonify, csrf
from web.backend.utils.context import request
from web.backend.domains.communication.chat_service import _DB_LOCK, connect_chat_db, fmt_display, utc_now_iso
from web.backend.utils.session import (
    current_auth_role,
    current_student_full_name,
)

_COMMENT_MAX_LENGTH = 500
_COMMENTS_PER_PAGE = 50


def register_comment_routes(students):
    @students.get("/api/resources/<int:resource_id>/comments")
    @csrf.exempt
    def api_list_comments(resource_id):
        with connect_chat_db() as conn:
            rows = conn.execute(
                """
                SELECT id, author_name, body, created_at
                FROM resource_comments
                WHERE resource_id = %s
                ORDER BY created_at ASC
                LIMIT %s
                """,
                (resource_id, _COMMENTS_PER_PAGE),
            ).fetchall()
        comments = [
            {
                "id": int(row["id"]),
                "authorName": str(row["author_name"]),
                "body": str(row["body"]),
                "createdAt": fmt_display(str(row["created_at"])),
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

        now = utc_now_iso()
        with _DB_LOCK:
            with connect_chat_db() as conn:
                exists = conn.execute(
                    "SELECT 1 FROM resources WHERE id = %s AND is_active = 1",
                    (resource_id,),
                ).fetchone()
                if not exists:
                    return jsonify({"error": "Resource not found."}), 404

                inserted = conn.execute(
                    """
                    INSERT INTO resource_comments (resource_id, author_name, body, created_at)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                    """,
                    (resource_id, author_name, body, now),
                )
                inserted_row = inserted.fetchone()
                comment_id = int(inserted_row["id"] or 0) if inserted_row else 0
                conn.commit()

        return jsonify({
            "comment": {
                "id": comment_id,
                "authorName": author_name,
                "body": body,
                "createdAt": fmt_display(now),
            }
        }), 201
