"""Resource-comment policy and transaction workflows."""

from datetime import datetime, timezone
import threading

from backend.core.database import connect_auth_db
from backend.repositories import resources as repository

COMMENT_MAX_LENGTH = 500
COMMENTS_PER_PAGE = 50
_COMMENT_LOCK = threading.Lock()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _display_time(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc).strftime("%-d %b %Y, %H:%M")
    except (TypeError, ValueError):
        return str(value)


def list_resource_comments(resource_id: int) -> list[dict]:
    with connect_auth_db() as conn:
        rows = repository.list_resource_comment_rows(conn, resource_id, COMMENTS_PER_PAGE)
    return [
        {
            "id": int(row["id"]),
            "authorName": str(row["author_name"]),
            "body": str(row["body"]),
            "createdAt": _display_time(str(row["created_at"])),
        }
        for row in rows
    ]


def add_resource_comment(resource_id: int, *, author_name: str, body: str) -> dict:
    now = _utc_now_iso()
    with _COMMENT_LOCK, connect_auth_db() as conn:
        if not repository.active_resource_exists(conn, resource_id):
            raise LookupError("Resource not found.")
        inserted = repository.insert_resource_comment(
            conn,
            resource_id=resource_id,
            author_name=author_name,
            body=body,
            created_at=now,
        )
        conn.commit()
    comment_id = int(inserted["id"] or 0) if inserted else 0
    return {
        "id": comment_id,
        "authorName": author_name,
        "body": body,
        "createdAt": _display_time(now),
    }
