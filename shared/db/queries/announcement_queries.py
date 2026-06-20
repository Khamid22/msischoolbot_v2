"""Schema DDL for the announcements table.

Lives in the query layer alongside the other ``ensure_*_schema`` helpers so the
framework-free shared services can provision it without importing web services.
"""


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


__all__ = ["ensure_announcements_schema"]
