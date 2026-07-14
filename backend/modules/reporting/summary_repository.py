"""Read-only subject summary helpers from the msi_v2 academic schema."""

from backend.modules.organization import canonical


def _subject_summary_select(where_clause="", params=()):
    return (
        f"""
        WITH base AS (
            SELECT
                gs.student_id AS enrollment_id,
                gs.student_id AS student_row_id,
                COALESCE(gs.legacy_public_dashboard_id, st.legacy_public_dashboard_id) AS public_dashboard_id,
                st.full_name,
                COALESCE(sch.school_key, '') AS school_key,
                COALESCE(sch.school_name, '') AS school_name,
                g.group_name,
                subj.subject_name,
                COALESCE(subj.subject_short, '') AS subject_short,
                COALESCE(hw.aap, 0)::double precision AS aap,
                COALESCE(att.ar, 0)::integer AS ar,
                COALESCE(ex.ep, 0)::integer AS ep,
                COALESCE(coins.total_coins, 0)::integer AS total_coins
            FROM msi_v2.group_students gs
            JOIN msi_v2.students st ON st.id = gs.student_id
            JOIN msi_v2.groups g ON g.id = gs.group_id
            LEFT JOIN msi_v2.schools sch ON sch.id = g.school_id
            JOIN msi_v2.subject_programs sp ON sp.id = g.program_id
            JOIN msi_v2.subjects subj ON subj.id = sp.subject_id
            LEFT JOIN (
                SELECT group_id, student_id, ROUND(AVG(score)::numeric, 1) AS aap
                FROM msi_v2.homework_scores
                WHERE score IS NOT NULL
                GROUP BY group_id, student_id
            ) hw ON hw.group_id = gs.group_id AND hw.student_id = gs.student_id
            LEFT JOIN (
                SELECT
                    group_id,
                    student_id,
                    ROUND(
                        (
                            SUM(CASE WHEN lower(attendance_status) IN ('present', 'justified', 'justified absent') THEN 1 ELSE 0 END)::numeric
                            / NULLIF(COUNT(*), 0)
                        ) * 100
                    )::integer AS ar
                FROM msi_v2.attendance_records
                WHERE trim(COALESCE(attendance_status, '')) <> ''
                GROUP BY group_id, student_id
            ) att ON att.group_id = gs.group_id AND att.student_id = gs.student_id
            LEFT JOIN (
                SELECT group_id, student_id, ROUND(AVG(score)::numeric)::integer AS ep
                FROM msi_v2.exam_results
                WHERE score IS NOT NULL
                GROUP BY group_id, student_id
            ) ex ON ex.group_id = gs.group_id AND ex.student_id = gs.student_id
            LEFT JOIN (
                SELECT student_id, SUM(amount)::integer AS total_coins
                FROM msi_v2.coin_events
                GROUP BY student_id
            ) coins ON coins.student_id = gs.student_id
            WHERE gs.enrollment_status = 'active'
              AND lower(g.group_name) <> 'online'
              {where_clause}
        ),
        scored AS (
            SELECT
                *,
                ROUND(((
                    ep
                    + aap
                    + CASE
                        WHEN ar <= 0 THEN 0
                        ELSE GREATEST(1, LEAST(9, ROUND((ar::numeric / 100) * 9)))
                      END
                ) / 3.0)::numeric, 1) AS composite_score
            FROM base
        )
        SELECT
            enrollment_id,
            student_row_id,
            public_dashboard_id,
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
            RANK() OVER (
                PARTITION BY subject_name
                ORDER BY composite_score DESC, ep DESC, aap DESC, ar DESC, lower(full_name) ASC, enrollment_id ASC
            )::integer AS rating_rank,
            COUNT(*) OVER (PARTITION BY subject_name)::integer AS rating_total,
            to_char(now() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS updated_at
        FROM scored
        ORDER BY lower(full_name) ASC, lower(subject_name) ASC, enrollment_id ASC
        """,
        tuple(params),
    )


def replace_subject_summary_rows(conn, rows):
    """Deprecated no-op kept for old call sites.

    Subject summaries are now derived directly from msi_v2 tables, so there is
    no cache table to clear or repopulate.
    """
    _ = conn, rows
    return None


def list_subject_summary_rows_by_full_name_norm(conn, full_name_norm):
    sql, params = _subject_summary_select()
    rows = conn.execute(sql, params).fetchall()
    normalized = canonical.normalize_text(full_name_norm)
    return [
        row
        for row in rows
        if canonical.normalize_text(row["full_name"]) == normalized
    ]


def list_subject_summary_rows(conn, school_key=""):
    normalized_school_key = str(school_key or "").strip().casefold()
    if normalized_school_key and normalized_school_key != "all":
        sql, params = _subject_summary_select(
            "AND lower(COALESCE(sch.school_key, '')) = lower(%s)",
            (normalized_school_key,),
        )
        return conn.execute(sql, params).fetchall()

    sql, params = _subject_summary_select()
    return conn.execute(sql, params).fetchall()


def list_subject_student_count_rows(conn):
    return conn.execute(
        """
        SELECT subj.subject_name,
               COUNT(DISTINCT gs.student_id)::integer AS count
        FROM msi_v2.group_students gs
        JOIN msi_v2.groups g ON g.id = gs.group_id
        JOIN msi_v2.subject_programs sp ON sp.id = g.program_id
        JOIN msi_v2.subjects subj ON subj.id = sp.subject_id
        WHERE gs.enrollment_status = 'active'
          AND lower(g.group_name) <> 'online'
        GROUP BY subj.id, subj.subject_name
        ORDER BY count DESC, lower(subj.subject_name) ASC
        """
    ).fetchall()


def list_subject_group_count_rows(conn):
    return conn.execute(
        """
        SELECT subj.subject_name,
               COUNT(DISTINCT g.id)::integer AS count
        FROM msi_v2.groups g
        JOIN msi_v2.subject_programs sp ON sp.id = g.program_id
        JOIN msi_v2.subjects subj ON subj.id = sp.subject_id
        WHERE lower(g.group_name) <> 'online'
          AND lower(COALESCE(g.status, 'active')) = 'active'
        GROUP BY subj.id, subj.subject_name
        ORDER BY count DESC, lower(subj.subject_name) ASC
        """
    ).fetchall()


__all__ = [
    "replace_subject_summary_rows",
    "list_subject_summary_rows_by_full_name_norm",
    "list_subject_summary_rows",
    "list_subject_student_count_rows",
    "list_subject_group_count_rows",
]
