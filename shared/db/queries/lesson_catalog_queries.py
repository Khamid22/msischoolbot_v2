"""Lesson catalog SQL query helpers."""

from shared.academics import canonical


def replace_lesson_catalog_rows(conn, rows):
    conn.execute("DELETE FROM lesson_catalog")

    if not rows:
        return

    payload_rows = []
    for row in rows:
        payload_rows.append(
            (
                canonical.canonical_subject_name(row.get("subject_name", ""))
                or str(row.get("subject_name", "")).strip(),
                str(row.get("group_name", "")),
                str(row.get("lesson_number", "")),
                str(row.get("lesson_topic", "")),
                canonical.format_date(row.get("lesson_date", "")),
                int(row.get("lesson_order", 0)),
                str(row.get("updated_at", "")),
            )
        )

    conn.executemany(
        """
        INSERT INTO lesson_catalog (
            subject_name,
            group_name,
            lesson_number,
            lesson_topic,
            lesson_date,
            lesson_order,
            updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        payload_rows,
    )


def list_lesson_catalog_rows_by_subject(conn, subject_name):
    return conn.execute(
        """
        SELECT
            group_name,
            lesson_number,
            lesson_topic,
            lesson_date,
            lesson_order,
            updated_at
        FROM lesson_catalog
        WHERE lower(subject_name) = lower(%s)
        ORDER BY lesson_order ASC, lesson_number ASC
        """,
        (canonical.canonical_subject_name(subject_name) or str(subject_name or "").strip(),),
    ).fetchall()


def list_lesson_catalog_rows_by_subject_group(conn, subject_name, group_name):
    return conn.execute(
        """
        SELECT
            group_name,
            lesson_number,
            lesson_topic,
            lesson_date,
            lesson_order,
            updated_at
        FROM lesson_catalog
        WHERE lower(subject_name) = lower(%s)
          AND lower(group_name) = lower(%s)
        ORDER BY lesson_order ASC, lesson_number ASC
        """,
        (canonical.canonical_subject_name(subject_name) or str(subject_name or "").strip(), group_name),
    ).fetchall()


__all__ = [
    "replace_lesson_catalog_rows",
    "list_lesson_catalog_rows_by_subject",
    "list_lesson_catalog_rows_by_subject_group",
]
