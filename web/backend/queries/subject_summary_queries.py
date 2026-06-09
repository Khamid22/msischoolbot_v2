"""Subject summary SQL query helpers."""


def replace_subject_summary_rows(conn, rows):
    conn.execute("DELETE FROM subject_summaries")

    if not rows:
        return

    payload_rows = []
    for row in rows:
        payload_rows.append(
            (
                int(row.get("sheet_student_id", 0)),
                str(row.get("full_name", "")),
                str(row.get("full_name_norm", "")),
                str(row.get("school_key", "")),
                str(row.get("school_name", "")),
                str(row.get("group_name", "")),
                str(row.get("subject_name", "")),
                str(row.get("subject_short", "")),
                float(row.get("aap", 0)),
                int(row.get("ar", 0)),
                int(row.get("ep", 0)),
                int(row.get("total_coins", 0)),
                int(row.get("rating_rank", 0)),
                int(row.get("rating_total", 0)),
                str(row.get("updated_at", "")),
            )
        )

    conn.executemany(
        """
        INSERT INTO subject_summaries (
            sheet_student_id,
            full_name,
            full_name_norm,
            school_key,
            school_name,
            group_name,
            subject_name,
            subject_short,
            aap,
            ar,
            ep,
            total_coins,
            rating_rank,
            rating_total,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        payload_rows,
    )


def list_subject_summary_rows_by_full_name_norm(conn, full_name_norm):
    return conn.execute(
        """
        SELECT
            sheet_student_id,
            full_name,
            school_key,
            school_name,
            group_name,
            subject_name,
            subject_short,
            aap,
            ar,
            ep,
            total_coins,
            rating_rank,
            rating_total,
            updated_at
        FROM subject_summaries
        WHERE full_name_norm = ?
        ORDER BY lower(subject_name) ASC, sheet_student_id ASC
        """,
        (full_name_norm,),
    ).fetchall()


def list_subject_summary_rows(conn, school_key = ""):
    normalized_school_key = str(school_key or "").strip().casefold()
    if normalized_school_key and normalized_school_key != "all":
        return conn.execute(
            """
            SELECT
                sheet_student_id,
                full_name,
                school_key,
                school_name,
                group_name,
                subject_name,
                subject_short,
                aap,
                ar,
                ep,
                total_coins,
                rating_rank,
                rating_total,
                updated_at
            FROM subject_summaries
            WHERE school_key = ?
            ORDER BY lower(full_name) ASC, lower(subject_name) ASC, sheet_student_id ASC
            """,
            (normalized_school_key,),
        ).fetchall()

    return conn.execute(
        """
        SELECT
            sheet_student_id,
            full_name,
            school_key,
            school_name,
            group_name,
            subject_name,
            subject_short,
            aap,
            ar,
            ep,
            total_coins,
            rating_rank,
            rating_total,
            updated_at
        FROM subject_summaries
        ORDER BY lower(full_name) ASC, lower(subject_name) ASC, sheet_student_id ASC
        """
    ).fetchall()


__all__ = [
    "replace_subject_summary_rows",
    "list_subject_summary_rows_by_full_name_norm",
    "list_subject_summary_rows",
]
