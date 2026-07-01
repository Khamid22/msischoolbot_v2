"""Schema DDL for the announcements table.

Lives in the query layer alongside the other ``ensure_*_schema`` helpers so the
framework-free shared services can provision it without importing web services.
"""


def ensure_announcements_schema(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS msi_v2.announcements (
            id BIGSERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            body TEXT NOT NULL DEFAULT '',
            audience TEXT NOT NULL DEFAULT 'all',
            priority TEXT NOT NULL DEFAULT 'normal',
            status TEXT NOT NULL DEFAULT 'published',
            pinned BOOLEAN NOT NULL DEFAULT false,
            author_staff_id BIGINT REFERENCES msi_v2.msi_staff(id) ON DELETE SET NULL,
            legacy_announcement_id BIGINT,
            published_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_announcements_status_pinned
        ON msi_v2.announcements(status, pinned, updated_at)
        """
    )


__all__ = ["ensure_announcements_schema"]
