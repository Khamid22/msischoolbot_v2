"""Lesson catalog helpers backed by subject program items."""

from database.academics import canonical


def replace_lesson_catalog_rows(conn, rows):
    """Legacy import hook.

    Subjects now come from full scheme-of-work imports, so this old row-level
    replacement hook intentionally does nothing.
    """
    return None


def list_lesson_catalog_rows_by_subject(conn, subject_name):
    return conn.execute(
        """
        SELECT
            '' AS group_name,
            i.lesson_number,
            i.title AS lesson_topic,
            '' AS lesson_date,
            i.item_order AS lesson_order,
            i.updated_at::text AS updated_at
        FROM msi_v2.subject_program_items i
        JOIN msi_v2.subject_programs p ON p.id = i.program_id
        JOIN msi_v2.subjects s ON s.id = p.subject_id
        WHERE lower(s.subject_name) = lower(%s)
          AND i.item_type = 'lesson'
        ORDER BY i.item_order ASC, i.lesson_number ASC
        """,
        (canonical.canonical_subject_name(subject_name) or str(subject_name or "").strip(),),
    ).fetchall()


def list_lesson_catalog_rows_by_subject_group(conn, subject_name, group_name):
    return list_lesson_catalog_rows_by_subject(conn, subject_name)


__all__ = [
    "replace_lesson_catalog_rows",
    "list_lesson_catalog_rows_by_subject",
    "list_lesson_catalog_rows_by_subject_group",
]
