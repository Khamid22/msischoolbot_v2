"""Lesson catalog SQL query helpers."""


def replace_lesson_catalog_rows(conn, rows):
    conn.execute("DELETE FROM lesson_catalog")

    if not rows:
        return

    payload_rows = []
    for row in rows:
        payload_rows.append(
            (
                str(row.get("subject_name", "")),
                str(row.get("group_name", "")),
                str(row.get("lesson_number", "")),
                str(row.get("lesson_topic", "")),
                str(row.get("lesson_date", "")),
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
        VALUES (?, ?, ?, ?, ?, ?, ?)
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
        WHERE lower(subject_name) = lower(?)
        ORDER BY lesson_order ASC, lesson_number ASC
        """,
        (subject_name,),
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
        WHERE lower(subject_name) = lower(?)
          AND lower(group_name) = lower(?)
        ORDER BY lesson_order ASC, lesson_number ASC
        """,
        (subject_name, group_name),
    ).fetchall()


__all__ = [
    "replace_lesson_catalog_rows",
    "list_lesson_catalog_rows_by_subject",
    "list_lesson_catalog_rows_by_subject_group",
]
