"""Reporting persistence for the Alembic-managed ``msi_v2`` schema."""

def list_msi_v2_table_names(conn):
    return conn.execute(
        "SELECT tablename AS name FROM pg_tables WHERE schemaname = 'msi_v2'"
    ).fetchall()


def list_subject_dashboard_rows(conn, subject_norm):
    return conn.execute(
        """
        SELECT COALESCE(gs.legacy_public_dashboard_id, st.legacy_public_dashboard_id) AS public_dashboard_id,
               st.full_name,
               COALESCE(hw.average_grade, 0) AS average_grade,
               COALESCE(coins.total_coins, 0) AS coins,
               sub.subject_name,
               g.group_name,
               g.group_code
        FROM msi_v2.group_students gs
        JOIN msi_v2.students st ON st.id = gs.student_id
        JOIN msi_v2.groups g ON g.id = gs.group_id
        JOIN msi_v2.subject_programs sp ON sp.id = g.program_id
        JOIN msi_v2.subjects sub ON sub.id = sp.subject_id
        LEFT JOIN (
            SELECT student_id, group_id, round(avg(score)::numeric, 1) AS average_grade
            FROM msi_v2.homework_scores
            WHERE score IS NOT NULL
            GROUP BY student_id, group_id
        ) hw ON hw.student_id = gs.student_id AND hw.group_id = gs.group_id
        LEFT JOIN (
            SELECT student_id, sum(amount)::integer AS total_coins
            FROM msi_v2.coin_events
            GROUP BY student_id
        ) coins ON coins.student_id = gs.student_id
        WHERE gs.enrollment_status = 'active'
          AND COALESCE(gs.legacy_public_dashboard_id, st.legacy_public_dashboard_id) IS NOT NULL
          AND lower(trim(sub.subject_name)) = %s
        ORDER BY g.group_name, st.full_name
        """,
        (subject_norm,),
    ).fetchall()


def list_internal_dataset_enrollment_rows(conn, normalized_school):
    return conn.execute(
        """
        SELECT gs.legacy_enrollment_id AS enrollment_id,
               COALESCE(gs.legacy_public_dashboard_id, st.legacy_public_dashboard_id) AS public_dashboard_id,
               st.full_name,
               COALESCE(hw.average_grade, 0) AS average_grade,
               COALESCE(coins.total_coins, 0) AS coins,
               s.school_key AS school_code,
               s.school_name,
               sub.subject_name,
               sub.subject_short AS subject_code,
               sp.lesson_count AS program_lesson_count,
               g.group_name,
               g.group_code
        FROM msi_v2.group_students gs
        JOIN msi_v2.students st ON st.id = gs.student_id
        JOIN msi_v2.groups g ON g.id = gs.group_id
        JOIN msi_v2.schools s ON s.id = g.school_id
        JOIN msi_v2.subject_programs sp ON sp.id = g.program_id
        JOIN msi_v2.subjects sub ON sub.id = sp.subject_id
        LEFT JOIN (
            SELECT student_id, group_id, round(avg(score)::numeric, 1) AS average_grade
            FROM msi_v2.homework_scores
            WHERE score IS NOT NULL
            GROUP BY student_id, group_id
        ) hw ON hw.student_id = gs.student_id AND hw.group_id = gs.group_id
        LEFT JOIN (
            SELECT student_id, sum(amount)::integer AS total_coins
            FROM msi_v2.coin_events
            GROUP BY student_id
        ) coins ON coins.student_id = gs.student_id
        WHERE gs.enrollment_status = 'active'
          AND COALESCE(gs.legacy_public_dashboard_id, st.legacy_public_dashboard_id) IS NOT NULL
          AND gs.legacy_enrollment_id IS NOT NULL
          AND lower(g.group_name) <> 'online'
          AND (%s = '' OR s.school_key = %s)
        ORDER BY sub.subject_name, g.group_name, st.full_name
        """,
        (normalized_school, normalized_school),
    ).fetchall()


def list_internal_dataset_lesson_rows(conn, normalized_school):
    return conn.execute(
        """
        SELECT s.school_key AS school_code,
               sub.subject_name,
               g.group_name,
               spi.lesson_number,
               spi.title AS topic,
               COALESCE(to_char(ls.session_date, 'DD/MM/YYYY'), '') AS lesson_date,
               spi.item_order AS lesson_order
        FROM msi_v2.lesson_sessions ls
        JOIN msi_v2.groups g ON g.id = ls.group_id
        JOIN msi_v2.schools s ON s.id = g.school_id
        JOIN msi_v2.subject_programs sp ON sp.id = g.program_id
        JOIN msi_v2.subjects sub ON sub.id = sp.subject_id
        JOIN msi_v2.subject_program_items spi ON spi.id = ls.program_item_id
        WHERE spi.item_type = 'lesson'
          AND lower(g.group_name) <> 'online'
          AND (%s = '' OR s.school_key = %s)
        ORDER BY sub.subject_name, g.group_name, spi.item_order, spi.lesson_number
        """,
        (normalized_school, normalized_school),
    ).fetchall()


def list_internal_dataset_attendance_rows(conn, normalized_school):
    return conn.execute(
        """
        SELECT gs.legacy_enrollment_id AS enrollment_id,
               spi.lesson_number AS lesson_label,
               spi.title AS topic,
               COALESCE(to_char(ls.session_date, 'DD/MM/YYYY'), '') AS lesson_date,
               '' AS attendance_type,
               ar.attendance_status AS status
        FROM msi_v2.attendance_records ar
        JOIN msi_v2.group_students gs
          ON gs.group_id = ar.group_id AND gs.student_id = ar.student_id
        JOIN msi_v2.lesson_sessions ls ON ls.id = ar.lesson_session_id
        JOIN msi_v2.subject_program_items spi ON spi.id = ls.program_item_id
        JOIN msi_v2.groups g ON g.id = ar.group_id
        JOIN msi_v2.schools s ON s.id = g.school_id
        WHERE gs.enrollment_status = 'active'
          AND gs.legacy_enrollment_id IS NOT NULL
          AND lower(g.group_name) <> 'online'
          AND (%s = '' OR s.school_key = %s)
        ORDER BY gs.legacy_enrollment_id, spi.item_order, spi.lesson_number
        """,
        (normalized_school, normalized_school),
    ).fetchall()


def list_internal_dataset_homework_rows(conn, normalized_school):
    return conn.execute(
        """
        SELECT gs.legacy_enrollment_id AS enrollment_id,
               spi.lesson_number AS lesson_label,
               spi.title AS topic,
               COALESCE(to_char(ls.session_date, 'DD/MM/YYYY'), '') AS lesson_date,
               'Homework' AS score_type,
               hs.score
        FROM msi_v2.homework_scores hs
        JOIN msi_v2.group_students gs
          ON gs.group_id = hs.group_id AND gs.student_id = hs.student_id
        JOIN msi_v2.lesson_sessions ls ON ls.id = hs.lesson_session_id
        JOIN msi_v2.subject_program_items spi ON spi.id = ls.program_item_id
        JOIN msi_v2.groups g ON g.id = hs.group_id
        JOIN msi_v2.schools s ON s.id = g.school_id
        WHERE gs.enrollment_status = 'active'
          AND gs.legacy_enrollment_id IS NOT NULL
          AND hs.score IS NOT NULL
          AND lower(g.group_name) <> 'online'
          AND (%s = '' OR s.school_key = %s)
        ORDER BY gs.legacy_enrollment_id, spi.item_order, spi.lesson_number
        """,
        (normalized_school, normalized_school),
    ).fetchall()


def list_internal_dataset_exam_rows(conn, normalized_school):
    return conn.execute(
        """
        SELECT DISTINCT ON (
               gs.legacy_enrollment_id,
               lower(COALESCE(er.exam_name, '')),
               lower(COALESCE(er.attempt, ''))
               )
               gs.legacy_enrollment_id AS enrollment_id,
               COALESCE(NULLIF(er.exam_name, ''), NULLIF(spi.title, ''), NULLIF(spi.lesson_number, ''), 'Exam') AS label,
               er.exam_name,
               er.attempt,
               er.score,
               COALESCE(spi.item_type, '') AS item_type,
               COALESCE(spi.title, '') AS item_title
        FROM msi_v2.exam_results er
        JOIN msi_v2.group_students gs
          ON gs.group_id = er.group_id AND gs.student_id = er.student_id
        JOIN msi_v2.groups g ON g.id = er.group_id
        JOIN msi_v2.schools s ON s.id = g.school_id
        LEFT JOIN msi_v2.subject_program_items spi ON spi.id = er.program_item_id
        WHERE gs.enrollment_status = 'active'
          AND gs.legacy_enrollment_id IS NOT NULL
          AND er.score IS NOT NULL
          AND lower(g.group_name) <> 'online'
          AND (%s = '' OR s.school_key = %s)
        ORDER BY gs.legacy_enrollment_id,
                 lower(COALESCE(er.exam_name, '')),
                 lower(COALESCE(er.attempt, '')),
                 er.updated_at DESC,
                 er.id DESC
        """,
        (normalized_school, normalized_school),
    ).fetchall()


def list_internal_overview_enrollment_rows(conn, normalized_school):
    return conn.execute(
        """
        SELECT concat(gs.group_id, ':', gs.student_id) AS enrollment_key,
               COALESCE(gs.legacy_public_dashboard_id, st.legacy_public_dashboard_id) AS public_dashboard_id,
               st.full_name,
               s.school_key AS school_code,
               s.school_name,
               sub.subject_name,
               g.group_name
        FROM msi_v2.group_students gs
        JOIN msi_v2.students st ON st.id = gs.student_id
        JOIN msi_v2.groups g ON g.id = gs.group_id
        JOIN msi_v2.schools s ON s.id = g.school_id
        JOIN msi_v2.subject_programs sp ON sp.id = g.program_id
        JOIN msi_v2.subjects sub ON sub.id = sp.subject_id
        WHERE gs.enrollment_status = 'active'
          AND lower(g.group_name) <> 'online'
          AND (%s = '' OR s.school_key = %s)
        ORDER BY sub.subject_name, g.group_name, st.full_name
        """,
        (normalized_school, normalized_school),
    ).fetchall()


def list_internal_overview_homework_rows(conn, normalized_school):
    return conn.execute(
        """
        SELECT concat(gs.group_id, ':', gs.student_id) AS enrollment_key,
               spi.lesson_number AS lesson_label,
               spi.title AS topic,
               COALESCE(to_char(ls.session_date, 'DD/MM/YYYY'), '') AS lesson_date,
               'Homework' AS score_type,
               hs.score
        FROM msi_v2.homework_scores hs
        JOIN msi_v2.group_students gs
          ON gs.group_id = hs.group_id AND gs.student_id = hs.student_id
        JOIN msi_v2.lesson_sessions ls ON ls.id = hs.lesson_session_id
        JOIN msi_v2.subject_program_items spi ON spi.id = ls.program_item_id
        JOIN msi_v2.groups g ON g.id = hs.group_id
        JOIN msi_v2.schools s ON s.id = g.school_id
        WHERE gs.enrollment_status = 'active'
          AND hs.score IS NOT NULL
          AND lower(g.group_name) <> 'online'
          AND (%s = '' OR s.school_key = %s)
        ORDER BY gs.group_id, gs.student_id, spi.item_order, spi.lesson_number
        """,
        (normalized_school, normalized_school),
    ).fetchall()


def list_internal_overview_exam_rows(conn, normalized_school):
    return conn.execute(
        """
        SELECT DISTINCT ON (
               gs.group_id,
               gs.student_id,
               lower(COALESCE(er.exam_name, '')),
               lower(COALESCE(er.attempt, ''))
               )
               concat(gs.group_id, ':', gs.student_id) AS enrollment_key,
               COALESCE(NULLIF(er.exam_name, ''), NULLIF(spi.title, ''), NULLIF(spi.lesson_number, ''), 'Exam') AS label,
               er.exam_name,
               er.attempt,
               er.score,
               COALESCE(spi.item_type, '') AS item_type,
               COALESCE(spi.title, '') AS item_title
        FROM msi_v2.exam_results er
        JOIN msi_v2.group_students gs
          ON gs.group_id = er.group_id AND gs.student_id = er.student_id
        JOIN msi_v2.groups g ON g.id = er.group_id
        JOIN msi_v2.schools s ON s.id = g.school_id
        LEFT JOIN msi_v2.subject_program_items spi ON spi.id = er.program_item_id
        WHERE gs.enrollment_status = 'active'
          AND er.score IS NOT NULL
          AND lower(g.group_name) <> 'online'
          AND (%s = '' OR s.school_key = %s)
        ORDER BY gs.group_id,
                 gs.student_id,
                 lower(COALESCE(er.exam_name, '')),
                 lower(COALESCE(er.attempt, '')),
                 er.updated_at DESC,
                 er.id DESC
        """,
        (normalized_school, normalized_school),
    ).fetchall()


def list_internal_overview_attendance_rows(conn, normalized_school):
    return conn.execute(
        """
        SELECT concat(gs.group_id, ':', gs.student_id) AS enrollment_key,
               COALESCE(to_char(ls.session_date, 'DD/MM/YYYY'), '') AS lesson_date,
               ar.attendance_status AS status
        FROM msi_v2.attendance_records ar
        JOIN msi_v2.group_students gs
          ON gs.group_id = ar.group_id AND gs.student_id = ar.student_id
        JOIN msi_v2.lesson_sessions ls ON ls.id = ar.lesson_session_id
        JOIN msi_v2.groups g ON g.id = ar.group_id
        JOIN msi_v2.schools s ON s.id = g.school_id
        WHERE gs.enrollment_status = 'active'
          AND lower(g.group_name) <> 'online'
          AND (%s = '' OR s.school_key = %s)
          AND ls.session_date IS NOT NULL
          AND ar.attendance_status IS NOT NULL
          AND ar.attendance_status <> ''
        ORDER BY gs.group_id, gs.student_id, ls.session_date
        """,
        (normalized_school, normalized_school),
    ).fetchall()


def get_enrollment_dashboard_row(
    conn,
    *,
    public_dashboard_id,
    normalized_school,
    normalized_subject,
    normalized_group,
):
    return conn.execute(
        """
        SELECT COALESCE(
                   gs.legacy_enrollment_id,
                   COALESCE(gs.legacy_public_dashboard_id, st.legacy_public_dashboard_id)
               ) AS id,
               COALESCE(gs.legacy_public_dashboard_id, st.legacy_public_dashboard_id) AS public_dashboard_id,
               st.full_name,
               COALESCE(hw.average_grade, 0) AS average_grade,
               COALESCE(coins.total_coins, 0) AS coins,
               s.school_key AS school_code,
               s.school_name,
               sub.subject_name,
               sub.subject_short AS subject_code,
               g.group_name,
               g.group_code,
               gs.group_id,
               gs.student_id,
               sp.lesson_count AS program_lesson_count
        FROM msi_v2.group_students gs
        JOIN msi_v2.students st ON st.id = gs.student_id
        JOIN msi_v2.groups g ON g.id = gs.group_id
        JOIN msi_v2.schools s ON s.id = g.school_id
        JOIN msi_v2.subject_programs sp ON sp.id = g.program_id
        JOIN msi_v2.subjects sub ON sub.id = sp.subject_id
        LEFT JOIN (
            SELECT student_id, group_id, round(avg(score)::numeric, 1) AS average_grade
            FROM msi_v2.homework_scores
            WHERE score IS NOT NULL
            GROUP BY student_id, group_id
        ) hw ON hw.student_id = gs.student_id AND hw.group_id = gs.group_id
        LEFT JOIN (
            SELECT student_id, sum(amount)::integer AS total_coins
            FROM msi_v2.coin_events
            GROUP BY student_id
        ) coins ON coins.student_id = gs.student_id
        WHERE COALESCE(gs.legacy_public_dashboard_id, st.legacy_public_dashboard_id) = %s
          AND gs.enrollment_status = 'active'
          AND lower(g.group_name) <> 'online'
          AND (%s = '' OR s.school_key = %s)
          AND (%s = '' OR lower(trim(regexp_replace(sub.subject_name, '[[:space:]]+', ' ', 'g'))) = %s)
          AND (%s = '' OR lower(trim(regexp_replace(g.group_name, '[[:space:]]+', ' ', 'g'))) = %s)
        LIMIT 1
        """,
        (
            int(public_dashboard_id),
            normalized_school,
            normalized_school,
            normalized_subject,
            normalized_subject,
            normalized_group,
            normalized_group,
        ),
    ).fetchone()


def list_enrollment_attendance_rows(conn, group_id, student_id):
    return conn.execute(
        """
        SELECT spi.lesson_number AS lesson_label,
               spi.title AS topic,
               COALESCE(to_char(ls.session_date, 'DD/MM/YYYY'), '') AS lesson_date,
               '' AS attendance_type,
               ar.attendance_status AS status
        FROM msi_v2.attendance_records ar
        JOIN msi_v2.lesson_sessions ls ON ls.id = ar.lesson_session_id
        JOIN msi_v2.subject_program_items spi ON spi.id = ls.program_item_id
        WHERE ar.group_id = %s
          AND ar.student_id = %s
        ORDER BY spi.item_order, spi.lesson_number
        """,
        (group_id, student_id),
    ).fetchall()


def list_enrollment_homework_rows(conn, group_id, student_id):
    return conn.execute(
        """
        SELECT spi.lesson_number AS lesson_label,
               spi.title AS topic,
               COALESCE(to_char(ls.session_date, 'DD/MM/YYYY'), '') AS lesson_date,
               'Homework' AS score_type,
               hs.score
        FROM msi_v2.homework_scores hs
        JOIN msi_v2.lesson_sessions ls ON ls.id = hs.lesson_session_id
        JOIN msi_v2.subject_program_items spi ON spi.id = ls.program_item_id
        WHERE hs.group_id = %s
          AND hs.student_id = %s
          AND hs.score IS NOT NULL
        ORDER BY spi.item_order, spi.lesson_number
        """,
        (group_id, student_id),
    ).fetchall()


def list_enrollment_exam_rows(conn, group_id, student_id):
    return conn.execute(
        """
        SELECT DISTINCT ON (
               lower(COALESCE(er.exam_name, '')),
               lower(COALESCE(er.attempt, ''))
               )
               COALESCE(NULLIF(er.exam_name, ''), NULLIF(spi.title, ''), NULLIF(spi.lesson_number, ''), 'Exam') AS label,
               er.exam_name,
               er.attempt,
               er.score,
               COALESCE(spi.item_type, '') AS item_type,
               COALESCE(spi.title, '') AS item_title
        FROM msi_v2.exam_results er
        LEFT JOIN msi_v2.subject_program_items spi ON spi.id = er.program_item_id
        WHERE er.group_id = %s
          AND er.student_id = %s
          AND er.score IS NOT NULL
        ORDER BY lower(COALESCE(er.exam_name, '')),
                 lower(COALESCE(er.attempt, '')),
                 er.updated_at DESC,
                 er.id DESC
        """,
        (group_id, student_id),
    ).fetchall()
