"""Parent-facing academic read helpers (msi_v2).

Used to render a linked child's subject indicators and recent lessons in the
parent portal / admin parent drawer. Students are matched by the stable
``legacy_student_row_id``.
"""


def list_parent_subject_indicator_rows(conn, student_row_id, full_name=""):
    # full_name is accepted for signature compatibility; matching is by the
    # reliable legacy student id (group_students always has a student row in v2).
    return conn.execute(
        """
        SELECT
            gs.legacy_enrollment_id AS enrollment_id,
            subj.subject_name,
            subj.subject_short,
            g.group_name AS group_name,
            COALESCE(hw.average_homework, 0) AS average_grade,
            COALESCE(coins.total_coins, 0) AS total_coins,
            '' AS updated_at,
            COALESCE(hw.average_homework, 0) AS homework_average,
            COALESCE(att.present_count, 0) AS present_count,
            COALESCE(att.absent_count, 0) AS absent_count,
            COALESCE(att.justified_count, 0) AS justified_count,
            COALESCE(ex.exam_average, 0) AS exam_average,
            COALESCE(progress.completed_lessons, 0) AS program_completed_lessons
        FROM msi_v2.group_students gs
        JOIN msi_v2.students st ON st.id = gs.student_id
        JOIN msi_v2.groups g ON g.id = gs.group_id
        JOIN msi_v2.subject_programs sp ON sp.id = g.program_id
        JOIN msi_v2.subjects subj ON subj.id = sp.subject_id
        LEFT JOIN (
            SELECT group_id, student_id, AVG(score) AS average_homework
            FROM msi_v2.homework_scores
            WHERE score IS NOT NULL
            GROUP BY group_id, student_id
        ) hw ON hw.group_id = gs.group_id AND hw.student_id = gs.student_id
        LEFT JOIN (
            SELECT group_id, student_id, SUM(amount)::int AS total_coins
            FROM msi_v2.coin_events
            GROUP BY group_id, student_id
        ) coins ON coins.group_id = gs.group_id AND coins.student_id = gs.student_id
        LEFT JOIN (
            SELECT group_id, student_id,
                   SUM(CASE WHEN lower(attendance_status) = 'present' THEN 1 ELSE 0 END) AS present_count,
                   SUM(CASE WHEN lower(attendance_status) = 'absent' THEN 1 ELSE 0 END) AS absent_count,
                   SUM(CASE WHEN lower(attendance_status) IN ('justified', 'justified absent') THEN 1 ELSE 0 END) AS justified_count
            FROM msi_v2.attendance_records
            WHERE trim(COALESCE(attendance_status, '')) <> ''
            GROUP BY group_id, student_id
        ) att ON att.group_id = gs.group_id AND att.student_id = gs.student_id
        LEFT JOIN (
            SELECT group_id, student_id, AVG(score) AS exam_average
            FROM msi_v2.exam_results
            WHERE score IS NOT NULL
            GROUP BY group_id, student_id
        ) ex ON ex.group_id = gs.group_id AND ex.student_id = gs.student_id
        LEFT JOIN (
            SELECT ar.group_id, ar.student_id, MAX(spi.item_order) AS completed_lessons
            FROM msi_v2.attendance_records ar
            JOIN msi_v2.lesson_sessions ls ON ls.id = ar.lesson_session_id
            JOIN msi_v2.subject_program_items spi ON spi.id = ls.program_item_id
            WHERE trim(COALESCE(ar.attendance_status, '')) <> ''
            GROUP BY ar.group_id, ar.student_id
        ) progress ON progress.group_id = gs.group_id AND progress.student_id = gs.student_id
        WHERE st.legacy_student_row_id = %s
          AND gs.enrollment_status = 'active'
          AND lower(g.group_name) <> 'online'
        ORDER BY lower(subj.subject_name) ASC, lower(g.group_name) ASC, gs.legacy_enrollment_id ASC
        """,
        (int(student_row_id),),
    ).fetchall()


def list_parent_recent_lesson_rows(conn, student_row_id, full_name="", limit=24):
    normalized_limit = max(1, min(int(limit or 24), 300))
    return conn.execute(
        """
        SELECT
            subj.subject_name,
            g.group_name AS group_name,
            spi.lesson_number AS lesson_number,
            spi.title AS lesson_topic,
            COALESCE(to_char(ls.session_date, 'DD/MM/YYYY'), '') AS lesson_date,
            spi.item_order AS lesson_order,
            ar.attendance_status AS attendance_status,
            COALESCE(to_char(ar.updated_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'), '') AS updated_at,
            'attendance' AS source
        FROM msi_v2.attendance_records ar
        JOIN msi_v2.group_students gs ON gs.group_id = ar.group_id AND gs.student_id = ar.student_id
        JOIN msi_v2.students st ON st.id = gs.student_id
        JOIN msi_v2.groups g ON g.id = gs.group_id
        JOIN msi_v2.subject_programs sp ON sp.id = g.program_id
        JOIN msi_v2.subjects subj ON subj.id = sp.subject_id
        JOIN msi_v2.lesson_sessions ls ON ls.id = ar.lesson_session_id
        JOIN msi_v2.subject_program_items spi ON spi.id = ls.program_item_id
        WHERE st.legacy_student_row_id = %s
          AND gs.enrollment_status = 'active'
          AND lower(g.group_name) <> 'online'
          AND ls.session_date IS NOT NULL
          AND trim(COALESCE(ar.attendance_status, '')) <> ''
        ORDER BY ls.session_date DESC, spi.item_order DESC, ar.updated_at DESC
        LIMIT %s
        """,
        (int(student_row_id), normalized_limit),
    ).fetchall()


def get_parent_child_row(conn, parent_id, student_row_id):
    """Confirm a parent (msi_v2.parents.id) is linked to a student (legacy id)."""
    return conn.execute(
        """
        SELECT l.parent_id, st.legacy_student_row_id AS student_row_id, l.created_at AS assigned_at
        FROM msi_v2.parent_student_links l
        JOIN msi_v2.students st ON st.id = l.student_id
        WHERE l.parent_id = %s AND st.legacy_student_row_id = %s
        """,
        (int(parent_id), int(student_row_id)),
    ).fetchone()


__all__ = [
    "list_parent_subject_indicator_rows",
    "list_parent_recent_lesson_rows",
    "get_parent_child_row",
]
