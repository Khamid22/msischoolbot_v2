"""Internal announcement storage and admin CRUD helpers."""

from datetime import datetime, timezone

from backend.core.database import connect_auth_db
from backend.modules.communications import announcements_repository

AUDIENCES = {
    "all",
    "students",
    "parents",
    "teachers",
    "year10",
    "year11",
    "trainees",
    "candidates",
    "staff",
}
PRIORITIES = {"info", "important", "urgent"}
STATUSES = {"published", "draft", "scheduled"}


def _utc_now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _connect():
    return connect_auth_db()


def _normalize_choice(value, allowed, default):
    normalized = str(value or "").strip().casefold()
    return normalized if normalized in allowed else default


def _row_to_dict(row):
    return {
        "id": int(row["id"]),
        "title": str(row["title"] or ""),
        "body": str(row["body"] or ""),
        "audience": str(row["audience"] or "all"),
        "priority": str(row["priority"] or "info"),
        "status": str(row["status"] or "draft"),
        "pinned": bool(row["pinned"]),
        "author": str(row.get("author") or ""),
        "views": int(row.get("views") or 0),
        "publishedAt": str(row["published_at"] or ""),
        "scheduledAt": str(row.get("scheduled_at") or ""),
        "createdAt": str(row["created_at"] or ""),
        "updatedAt": str(row["updated_at"] or ""),
    }


def list_announcements(include_drafts=True):
    with _connect() as conn:
        rows = announcements_repository.list_announcement_rows(conn, include_drafts=include_drafts)
    return [_row_to_dict(row) for row in rows]


def create_announcement(
    *,
    title,
    body,
    audience="all",
    priority="info",
    status="draft",
    pinned=False,
    author="",
    scheduled_at="",
):
    normalized_title = str(title or "").strip()
    normalized_body = str(body or "").strip()
    if not normalized_title:
        raise ValueError("Title is required.")
    if not normalized_body:
        raise ValueError("Message is required.")

    now = _utc_now_iso()
    normalized_status = _normalize_choice(status, STATUSES, "draft")
    published_at = now if normalized_status == "published" else ""
    with _connect() as conn:
        inserted = announcements_repository.insert_announcement_row(
            conn,
            title=normalized_title,
            body=normalized_body,
            audience=_normalize_choice(audience, AUDIENCES, "all"),
            priority=_normalize_choice(priority, PRIORITIES, "info"),
            status=normalized_status,
            pinned=bool(pinned),
            published_at=published_at,
            created_at=now,
            updated_at=now,
        )
        announcement_id = int(inserted["id"] or 0) if inserted else 0
        conn.commit()
        row = announcements_repository.get_announcement_row(conn, announcement_id)
    return _row_to_dict(row)


def update_announcement(announcement_id, **values):
    now = _utc_now_iso()
    with _connect() as conn:
        existing = announcements_repository.get_announcement_row(conn, announcement_id)
        if not existing:
            raise ValueError("Announcement not found.")

        title_value = existing["title"] if values.get("title") is None else values.get("title")
        body_value = existing["body"] if values.get("body") is None else values.get("body")
        title = str(title_value or "").strip()
        body = str(body_value or "").strip()
        if not title:
            raise ValueError("Title is required.")
        if not body:
            raise ValueError("Message is required.")

        old_status = str(existing["status"] or "draft")
        status_value = old_status if values.get("status") is None else values.get("status")
        status = _normalize_choice(status_value, STATUSES, old_status)
        published_at = str(existing["published_at"] or "")
        if status == "published" and old_status != "published" and not published_at:
            published_at = now
        if status != "published":
            published_at = ""

        announcements_repository.update_announcement_row(
            conn,
            announcement_id,
            title=title,
            body=body,
            audience=_normalize_choice(
                existing["audience"] if values.get("audience") is None else values.get("audience"),
                AUDIENCES,
                "all",
            ),
            priority=_normalize_choice(
                existing["priority"] if values.get("priority") is None else values.get("priority"),
                PRIORITIES,
                "info",
            ),
            status=status,
            pinned=bool(existing["pinned"] if values.get("pinned") is None else values.get("pinned")),
            published_at=published_at,
            updated_at=now,
        )
        conn.commit()
        row = announcements_repository.get_announcement_row(conn, announcement_id)
    return _row_to_dict(row)


def delete_announcement(announcement_id):
    with _connect() as conn:
        cur = announcements_repository.delete_announcement_row(conn, announcement_id)
        conn.commit()
    return cur.rowcount > 0
