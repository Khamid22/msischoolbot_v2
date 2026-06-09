"""Internal announcement storage and admin CRUD helpers."""

from datetime import datetime

from web.backend import queries

AUDIENCES = {"all", "students", "teachers", "year10", "year11"}
PRIORITIES = {"info", "important", "urgent"}
STATUSES = {"published", "draft", "scheduled"}


def _utc_now_iso():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _connect():
    return queries.connect_auth_db()


def ensure_announcements_schema(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS announcements (
            id BIGSERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            audience TEXT NOT NULL DEFAULT 'all',
            priority TEXT NOT NULL DEFAULT 'info',
            status TEXT NOT NULL DEFAULT 'draft',
            pinned INTEGER NOT NULL DEFAULT 0,
            author TEXT NOT NULL DEFAULT '',
            views INTEGER NOT NULL DEFAULT 0,
            published_at TEXT NOT NULL DEFAULT '',
            scheduled_at TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_announcements_status_pinned
        ON announcements(status, pinned, updated_at)
        """
    )


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
        "author": str(row["author"] or ""),
        "views": int(row["views"] or 0),
        "publishedAt": str(row["published_at"] or ""),
        "scheduledAt": str(row["scheduled_at"] or ""),
        "createdAt": str(row["created_at"] or ""),
        "updatedAt": str(row["updated_at"] or ""),
    }


def list_announcements(include_drafts=True):
    with _connect() as conn:
        ensure_announcements_schema(conn)
        if include_drafts:
            rows = conn.execute(
                """
                SELECT * FROM announcements
                ORDER BY pinned DESC, updated_at DESC, id DESC
                """
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM announcements
                WHERE status = 'published'
                ORDER BY pinned DESC, published_at DESC, updated_at DESC, id DESC
                """
            ).fetchall()
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
        ensure_announcements_schema(conn)
        cur = conn.execute(
            """
            INSERT INTO announcements (
                title, body, audience, priority, status, pinned, author, views,
                published_at, scheduled_at, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?)
            """,
            (
                normalized_title,
                normalized_body,
                _normalize_choice(audience, AUDIENCES, "all"),
                _normalize_choice(priority, PRIORITIES, "info"),
                normalized_status,
                int(bool(pinned)),
                str(author or "").strip(),
                published_at,
                str(scheduled_at or "").strip(),
                now,
                now,
            ),
        )
        conn.commit()
        announcement_id = int(cur.lastrowid)
        row = conn.execute("SELECT * FROM announcements WHERE id = ?", (announcement_id,)).fetchone()
    return _row_to_dict(row)


def update_announcement(announcement_id, **values):
    now = _utc_now_iso()
    with _connect() as conn:
        ensure_announcements_schema(conn)
        existing = conn.execute(
            "SELECT * FROM announcements WHERE id = ?",
            (int(announcement_id),),
        ).fetchone()
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

        conn.execute(
            """
            UPDATE announcements
            SET title = ?, body = ?, audience = ?, priority = ?, status = ?,
                pinned = ?, published_at = ?, scheduled_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                title,
                body,
                _normalize_choice(
                    existing["audience"] if values.get("audience") is None else values.get("audience"),
                    AUDIENCES,
                    "all",
                ),
                _normalize_choice(
                    existing["priority"] if values.get("priority") is None else values.get("priority"),
                    PRIORITIES,
                    "info",
                ),
                status,
                int(bool(existing["pinned"] if values.get("pinned") is None else values.get("pinned"))),
                published_at,
                str(
                    (
                        existing["scheduled_at"]
                        if values.get("scheduled_at") is None
                        else values.get("scheduled_at")
                    )
                    or ""
                ).strip(),
                now,
                int(announcement_id),
            ),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM announcements WHERE id = ?", (int(announcement_id),)).fetchone()
    return _row_to_dict(row)


def delete_announcement(announcement_id):
    with _connect() as conn:
        ensure_announcements_schema(conn)
        cur = conn.execute(
            "DELETE FROM announcements WHERE id = ?",
            (int(announcement_id),),
        )
        conn.commit()
    return cur.rowcount > 0
