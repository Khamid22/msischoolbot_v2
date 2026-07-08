"""Resource comment reads/writes."""

from __future__ import annotations

from backend.domains.communication.chat_service import (
    _DB_LOCK,
    connect_chat_db,
    fmt_display,
    utc_now_iso,
)
from backend.domains.resources import queries

COMMENT_MAX_LENGTH = 500
COMMENTS_PER_PAGE = 50


def list_resource_comments(resource_id: int) -> list[dict]:
    with connect_chat_db() as conn:
        queries.ensure_resource_comments_schema(conn)
        rows = conn.execute(
            """
            SELECT id, author_name, body, created_at
            FROM msi_v2.resource_comments
            WHERE resource_id = %s
            ORDER BY created_at ASC
            LIMIT %s
            """,
            (resource_id, COMMENTS_PER_PAGE),
        ).fetchall()
    return [
        {
            "id": int(row["id"]),
            "authorName": str(row["author_name"]),
            "body": str(row["body"]),
            "createdAt": fmt_display(str(row["created_at"])),
        }
        for row in rows
    ]


def add_resource_comment(resource_id: int, *, author_name: str, body: str) -> dict:
    """Insert a comment. Raises LookupError when the resource does not exist."""
    now = utc_now_iso()
    with _DB_LOCK:
        with connect_chat_db() as conn:
            queries.ensure_resource_comments_schema(conn)
            exists = conn.execute(
                "SELECT 1 FROM msi_v2.resources WHERE id = %s AND is_active IS TRUE",
                (resource_id,),
            ).fetchone()
            if not exists:
                raise LookupError("Resource not found.")

            inserted = conn.execute(
                """
                INSERT INTO msi_v2.resource_comments (resource_id, author_name, body, created_at)
                VALUES (%s, %s, %s, %s::timestamptz)
                RETURNING id
                """,
                (resource_id, author_name, body, now),
            )
            inserted_row = inserted.fetchone()
            comment_id = int(inserted_row["id"] or 0) if inserted_row else 0
            conn.commit()

    return {
        "id": comment_id,
        "authorName": author_name,
        "body": body,
        "createdAt": fmt_display(now),
    }
