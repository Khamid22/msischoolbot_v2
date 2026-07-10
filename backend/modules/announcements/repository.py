"""Announcement queries for the Alembic-managed ``msi_v2`` schema."""


def list_announcement_rows(conn, include_drafts=True):
    if include_drafts:
        return conn.execute(
            """
            SELECT *, '' AS author, 0 AS views, '' AS scheduled_at
            FROM msi_v2.announcements
            ORDER BY pinned DESC, updated_at DESC, id DESC
            """
        ).fetchall()
    return conn.execute(
        """
        SELECT *, '' AS author, 0 AS views, '' AS scheduled_at
        FROM msi_v2.announcements
        WHERE status = 'published'
        ORDER BY pinned DESC, published_at DESC, updated_at DESC, id DESC
        """
    ).fetchall()


def insert_announcement_row(
    conn,
    *,
    title,
    body,
    audience,
    priority,
    status,
    pinned,
    published_at,
    created_at,
    updated_at,
):
    return conn.execute(
        """
        INSERT INTO msi_v2.announcements (
            title, body, audience, priority, status, pinned,
            published_at, created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s::timestamptz, %s::timestamptz, %s::timestamptz)
        RETURNING id
        """,
        (
            title,
            body,
            audience,
            priority,
            status,
            bool(pinned),
            published_at or None,
            created_at,
            updated_at,
        ),
    ).fetchone()


def get_announcement_row(conn, announcement_id):
    return conn.execute(
        "SELECT *, '' AS author, 0 AS views, '' AS scheduled_at FROM msi_v2.announcements WHERE id = %s",
        (int(announcement_id),),
    ).fetchone()


def update_announcement_row(
    conn,
    announcement_id,
    *,
    title,
    body,
    audience,
    priority,
    status,
    pinned,
    published_at,
    updated_at,
):
    conn.execute(
        """
        UPDATE msi_v2.announcements
        SET title = %s, body = %s, audience = %s, priority = %s, status = %s,
            pinned = %s, published_at = %s::timestamptz, updated_at = %s::timestamptz
        WHERE id = %s
        """,
        (
            title,
            body,
            audience,
            priority,
            status,
            bool(pinned),
            published_at or None,
            updated_at,
            int(announcement_id),
        ),
    )


def delete_announcement_row(conn, announcement_id):
    return conn.execute(
        "DELETE FROM msi_v2.announcements WHERE id = %s",
        (int(announcement_id),),
    )


__all__ = [
    "delete_announcement_row",
    "get_announcement_row",
    "insert_announcement_row",
    "list_announcement_rows",
    "update_announcement_row",
]
