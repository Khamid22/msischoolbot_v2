"""Academic operational SQL helpers.

DB-5 owns academic query access here while the physical database schema remains
``msi_v2``. Service modules keep shaping payloads; this module owns raw
academic SQL for subjects, programs, groups, enrollments, lessons and internal
dashboard datasets.
"""

_GROUP_MATCH = "(g.legacy_group_id = %s OR (g.legacy_group_id IS NULL AND g.id = %s))"


def list_msi_v2_table_names(conn):
    return conn.execute(
        "SELECT tablename AS name FROM pg_tables WHERE schemaname = 'msi_v2'"
    ).fetchall()


def mint_legacy_id(conn, table, column, floor):
    row = conn.execute(
        f"SELECT coalesce(max({column}), 0) AS m FROM msi_v2.{table}"
    ).fetchone()
    return max(int(row["m"] or 0), int(floor)) + 1


def get_group_by_legacy_or_id(conn, group_id):
    return conn.execute(
        f"""
        SELECT g.id, g.school_id, g.program_id, g.group_name, g.class_id, g.set_name,
               s.school_key, s.school_name,
               subj.id AS subject_id, subj.subject_name
        FROM msi_v2.groups g
        JOIN msi_v2.schools s ON s.id = g.school_id
        JOIN msi_v2.subject_programs sp ON sp.id = g.program_id
        JOIN msi_v2.subjects subj ON subj.id = sp.subject_id
        WHERE {_GROUP_MATCH}
        """,
        (int(group_id or 0), int(group_id or 0)),
    ).fetchone()


def get_program_teaching_session_count(conn, program_id):
    row = conn.execute(
        """SELECT coalesce(sum(greatest(spi.lesson_count, 1)), 0) AS total
           FROM msi_v2.subject_program_items spi
           WHERE spi.program_id = %s AND spi.item_type = 'lesson'""",
        (int(program_id),),
    ).fetchone()
    return int(row["total"] or 0) if row else 0


def get_teacher_v2_id_by_legacy_or_id(conn, teacher_id):
    return conn.execute(
        "SELECT id FROM msi_v2.teachers WHERE legacy_teacher_id = %s OR id = %s LIMIT 1",
        (int(teacher_id or 0), int(teacher_id or 0)),
    ).fetchone()


def list_student_codes_with_prefix(conn, prefix):
    return conn.execute(
        "SELECT student_code FROM msi_v2.students WHERE upper(student_code) LIKE %s",
        (f"{str(prefix or '').strip().upper()}%",),
    ).fetchall()


def list_school_rows(conn):
    return conn.execute(
        "SELECT id, school_key AS code, school_name AS name FROM msi_v2.schools ORDER BY school_name"
    ).fetchall()


def list_subject_rows(conn):
    return conn.execute(
        """
        SELECT id, subject_name AS name, subject_key AS key,
               subject_short AS code, subject_short AS short_name
        FROM msi_v2.subjects
        WHERE status = 'active'
        ORDER BY subject_name
        """
    ).fetchall()


def list_group_rows(conn):
    return conn.execute(
        """
        SELECT coalesce(g.legacy_group_id, g.id) AS id,
               g.school_id, s.school_key AS school_code,
               subj.id AS subject_id, subj.subject_name AS subject_name,
               g.class_id, c.class_name, g.group_name AS name, g.group_code AS code,
               g.set_name,
               (g.legacy_group_id IS NOT NULL AND g.legacy_group_id < 9000000000) AS is_imported,
               CASE WHEN EXISTS (
                 SELECT 1 FROM msi_v2.group_schedule_rules rule
                 WHERE rule.group_id = g.id AND rule.status = 'active'
               ) AND EXISTS (
                 SELECT 1 FROM msi_v2.group_students member
                 WHERE member.group_id = g.id AND member.enrollment_status = 'active'
               ) THEN 'active'
                 WHEN g.legacy_group_id IS NOT NULL AND g.legacy_group_id < 9000000000 THEN 'imported'
                 ELSE 'new' END AS setup_status,
               count(*) FILTER (WHERE gs.enrollment_status = 'active') AS students_count,
               count(*) FILTER (WHERE gs.enrollment_status = 'disqualified') AS disqualified_count
        FROM msi_v2.groups g
        JOIN msi_v2.schools s ON s.id = g.school_id
        LEFT JOIN msi_v2.classes c ON c.id = g.class_id
        JOIN msi_v2.subject_programs sp ON sp.id = g.program_id
        JOIN msi_v2.subjects subj ON subj.id = sp.subject_id
        LEFT JOIN msi_v2.group_students gs ON gs.group_id = g.id
        WHERE lower(g.group_name) <> 'online'
        GROUP BY g.id, g.legacy_group_id, g.school_id, s.school_key, s.school_name,
                 subj.id, subj.subject_name, g.class_id, c.class_name,
                 g.group_name, g.group_code, g.set_name
        ORDER BY s.school_name, subj.subject_name, g.group_name
        """
    ).fetchall()


def list_class_rows(conn):
    return conn.execute(
        """
        SELECT c.id, c.school_id, s.school_key AS school_code,
               c.class_name AS name, c.class_code AS code, c.status,
               count(DISTINCT g.id) AS groups_count,
               count(DISTINCT cs.student_id) FILTER (
                 WHERE cs.enrollment_status = 'active'
               ) AS students_count
        FROM msi_v2.classes c
        JOIN msi_v2.schools s ON s.id = c.school_id
        LEFT JOIN msi_v2.groups g ON g.class_id = c.id
        LEFT JOIN msi_v2.class_students cs ON cs.class_id = c.id
        GROUP BY c.id, s.school_key, s.school_name
        ORDER BY s.school_name, c.class_name
        """
    ).fetchall()


def get_class(conn, class_id):
    return conn.execute(
        """SELECT c.*, s.school_key, s.school_name
           FROM msi_v2.classes c JOIN msi_v2.schools s ON s.id = c.school_id
           WHERE c.id = %s""",
        (int(class_id),),
    ).fetchone()


def get_class_by_school_and_name(conn, school_id, class_name):
    return conn.execute(
        "SELECT * FROM msi_v2.classes WHERE school_id = %s AND lower(btrim(class_name)) = lower(btrim(%s))",
        (int(school_id), class_name),
    ).fetchone()


def insert_class(conn, school_id, class_name, class_code):
    return conn.execute(
        """INSERT INTO msi_v2.classes (school_id, class_name, class_code)
           VALUES (%s, %s, %s) RETURNING *""",
        (int(school_id), class_name, class_code),
    ).fetchone()


def upsert_class_student(conn, class_id, student_id):
    conn.execute(
        """INSERT INTO msi_v2.class_students (class_id, student_id)
           VALUES (%s, %s)
           ON CONFLICT (class_id, student_id) DO UPDATE SET
             enrollment_status = 'active', left_at = NULL""",
        (int(class_id), int(student_id)),
    )


def list_enrollment_rows(conn):
    return conn.execute(
        """
        SELECT gs.legacy_enrollment_id AS id,
               coalesce(gs.legacy_public_dashboard_id, st.legacy_public_dashboard_id) AS public_dashboard_id,
               st.full_name,
               g.school_id, s.school_key AS school_code, s.school_name,
               subj.id AS subject_id, subj.subject_name,
               coalesce(g.legacy_group_id, g.id) AS group_id, g.group_name,
               (gs.enrollment_status = 'active') AS active, gs.enrollment_status
        FROM msi_v2.group_students gs
        JOIN msi_v2.students st ON st.id = gs.student_id
        JOIN msi_v2.groups g ON g.id = gs.group_id
        JOIN msi_v2.schools s ON s.id = g.school_id
        JOIN msi_v2.subject_programs sp ON sp.id = g.program_id
        JOIN msi_v2.subjects subj ON subj.id = sp.subject_id
        WHERE lower(g.group_name) <> 'online'
          AND gs.enrollment_status = 'active'
          AND gs.legacy_enrollment_id IS NOT NULL
        ORDER BY s.school_name, subj.subject_name, g.group_name, st.full_name
        """
    ).fetchall()


def get_enrollment_summary_row(conn):
    return conn.execute(
        """
        SELECT
          count(*) FILTER (WHERE gs.enrollment_status = 'active') AS active_enrollments,
          count(DISTINCT lower(trim(st.full_name))) FILTER (
            WHERE gs.enrollment_status = 'active' AND trim(st.full_name) <> ''
          ) AS active_unique_students,
          count(*) FILTER (WHERE gs.enrollment_status = 'disqualified') AS disqualified_enrollments
        FROM msi_v2.group_students gs
        JOIN msi_v2.students st ON st.id = gs.student_id
        JOIN msi_v2.groups g ON g.id = gs.group_id
        WHERE lower(g.group_name) <> 'online'
        """
    ).fetchone()


def list_lesson_rows(conn):
    return conn.execute(
        """
        SELECT ls.id, g.school_id, subj.id AS subject_id,
               coalesce(g.legacy_group_id, g.id) AS group_id,
               s.school_key AS school_code, subj.subject_name,
               g.group_name, spi.lesson_number, spi.title AS lesson_topic,
               coalesce(to_char(ls.session_date, 'DD/MM/YYYY'), '') AS lesson_date,
               spi.item_order AS lesson_order
        FROM msi_v2.lesson_sessions ls
        JOIN msi_v2.subject_program_items spi ON spi.id = ls.program_item_id
        JOIN msi_v2.groups g ON g.id = ls.group_id
        JOIN msi_v2.schools s ON s.id = g.school_id
        JOIN msi_v2.subject_programs sp ON sp.id = g.program_id
        JOIN msi_v2.subjects subj ON subj.id = sp.subject_id
        WHERE spi.item_type = 'lesson' AND lower(g.group_name) <> 'online'
        ORDER BY s.school_name, subj.subject_name, g.group_name, spi.item_order
        """
    ).fetchall()


def list_curriculum_program_rows(conn):
    return conn.execute(
        """
        SELECT sp.id, subj.subject_key, subj.subject_name, subj.subject_short,
               sp.source_file, sp.total_items, sp.lesson_count, sp.exam_count,
               sp.updated_at::text AS updated_at,
               1 AS db_subject_count,
               (
                 SELECT count(*) FROM msi_v2.groups g
                 WHERE g.program_id = sp.id AND lower(g.group_name) <> 'online'
               ) AS group_count
        FROM msi_v2.subject_programs sp
        JOIN msi_v2.subjects subj ON subj.id = sp.subject_id
        WHERE sp.status = 'active'
        ORDER BY subj.subject_name
        """
    ).fetchall()


def list_curriculum_item_rows(conn):
    return conn.execute(
        """
        SELECT spi.id, spi.program_id, subj.subject_key, subj.subject_name,
               spi.item_order, spi.lesson_number, spi.item_type, spi.title,
               spi.term_label, spi.week_label, spi.specification_points,
               spi.book_pages, spi.lesson_count, spi.duration_hours
        FROM msi_v2.subject_program_items spi
        JOIN msi_v2.subject_programs sp ON sp.id = spi.program_id
        JOIN msi_v2.subjects subj ON subj.id = sp.subject_id
        ORDER BY subj.subject_name, spi.item_order
        """
    ).fetchall()


def get_school_by_key(conn, school_code):
    return conn.execute(
        "SELECT id FROM msi_v2.schools WHERE lower(school_key) = lower(%s)",
        (school_code,),
    ).fetchone()


def insert_school(conn, code, name):
    conn.execute(
        "INSERT INTO msi_v2.schools (school_key, school_name) VALUES (%s, %s)",
        (code, name),
    )


def upsert_subject(conn, key, name, short_name):
    conn.execute(
        """
        INSERT INTO msi_v2.subjects (subject_key, subject_name, subject_short, status)
        VALUES (%s, %s, %s, 'active')
        ON CONFLICT ((lower(subject_key))) DO UPDATE SET
          subject_name = excluded.subject_name,
          subject_short = excluded.subject_short,
          status = 'active',
          updated_at = now()
        """,
        (key, name, short_name),
    )


def get_subject_program_by_subject_key(conn, subject_key):
    return conn.execute(
        """
        SELECT sp.id
        FROM msi_v2.subject_programs sp
        JOIN msi_v2.subjects subj ON subj.id = sp.subject_id
        WHERE lower(subj.subject_key) = lower(%s) AND sp.status = 'active'
        ORDER BY sp.id DESC
        LIMIT 1
        """,
        (subject_key,),
    ).fetchone()


def get_existing_group(conn, school_id, program_id, group_name):
    return conn.execute(
        """
        SELECT id FROM msi_v2.groups
        WHERE school_id = %s AND program_id = %s AND lower(group_name) = lower(%s)
        """,
        (int(school_id), int(program_id), group_name),
    ).fetchone()


def group_belongs_to_school(conn, group_name, school_code):
    return conn.execute(
        """
        SELECT 1
        FROM msi_v2.groups g
        JOIN msi_v2.schools s ON s.id = g.school_id
        WHERE g.group_name = %s
          AND lower(s.school_key) = lower(%s)
        LIMIT 1
        """,
        (group_name, school_code),
    ).fetchone() is not None


def update_group_code(conn, group_id, group_code):
    conn.execute(
        "UPDATE msi_v2.groups SET group_code = %s, updated_at = now() WHERE id = %s",
        (str(group_code or ""), int(group_id)),
    )


def update_group_class(conn, group_id, class_id, set_name):
    conn.execute(
        """UPDATE msi_v2.groups
           SET class_id = %s, set_name = %s, updated_at = now()
           WHERE id = %s""",
        (int(class_id), str(set_name or "Set 1"), int(group_id)),
    )


def insert_group(conn, school_id, program_id, group_name, group_code, legacy_group_id, *, class_id=None, set_name="Set 1"):
    conn.execute(
        """
        INSERT INTO msi_v2.groups (
          school_id, program_id, group_name, group_code, status, legacy_group_id,
          class_id, set_name
        ) VALUES (%s, %s, %s, %s, 'active', %s, %s, %s)
        """,
        (int(school_id), int(program_id), group_name, str(group_code or ""),
         int(legacy_group_id), int(class_id) if class_id else None, str(set_name or "Set 1")),
    )


def list_students_by_school_id(conn, school_id):
    return conn.execute(
        "SELECT id, full_name, student_code FROM msi_v2.students WHERE school_id = %s",
        (int(school_id),),
    ).fetchall()


def insert_student(conn, *, student_code, full_name, school_id, legacy_student_row_id):
    return conn.execute(
        """
        INSERT INTO msi_v2.students (
            student_code, full_name, school_id, status,
            legacy_student_row_id
        )
        VALUES (%s, %s, %s, 'active', %s)
        RETURNING id
        """,
        (student_code, full_name, int(school_id), int(legacy_student_row_id)),
    ).fetchone()


def upsert_group_student_enrollment(
    conn,
    *,
    group_id,
    student_id,
    legacy_enrollment_id,
    legacy_public_dashboard_id,
):
    return conn.execute(
        """
        INSERT INTO msi_v2.group_students (
            group_id, student_id, enrollment_status, joined_at,
            legacy_enrollment_id, legacy_public_dashboard_id
        )
        VALUES (%s, %s, 'active', now(), %s, %s)
        ON CONFLICT (group_id, student_id) DO UPDATE SET
            enrollment_status = 'active',
            left_at = NULL
        RETURNING legacy_enrollment_id
        """,
        (
            int(group_id),
            int(student_id),
            int(legacy_enrollment_id),
            int(legacy_public_dashboard_id),
        ),
    ).fetchone()


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


def list_lesson_catalog_rows_by_subject(conn, subject_name):
    """List lesson items from the canonical active program for a subject."""
    return conn.execute(
        """
        SELECT
            spi.lesson_number,
            spi.title AS lesson_topic,
            '' AS lesson_date,
            spi.item_order AS lesson_order,
            spi.updated_at::text AS updated_at
        FROM msi_v2.subject_program_items spi
        JOIN msi_v2.subject_programs sp ON sp.id = spi.program_id
        JOIN msi_v2.subjects s ON s.id = sp.subject_id
        WHERE lower(s.subject_name) = lower(%s)
          AND s.status = 'active'
          AND sp.status = 'active'
          AND spi.item_type = 'lesson'
        ORDER BY spi.item_order ASC, spi.lesson_number ASC
        """,
        (str(subject_name or "").strip(),),
    ).fetchall()


__all__ = [
    "get_enrollment_dashboard_row",
    "get_enrollment_summary_row",
    "get_existing_group",
    "group_belongs_to_school",
    "get_group_by_legacy_or_id",
    "get_school_by_key",
    "get_subject_program_by_subject_key",
    "get_teacher_v2_id_by_legacy_or_id",
    "insert_group",
    "insert_school",
    "insert_student",
    "list_curriculum_item_rows",
    "list_curriculum_program_rows",
    "list_enrollment_attendance_rows",
    "list_enrollment_exam_rows",
    "list_enrollment_homework_rows",
    "list_enrollment_rows",
    "list_group_rows",
    "list_internal_dataset_attendance_rows",
    "list_internal_dataset_enrollment_rows",
    "list_internal_dataset_exam_rows",
    "list_internal_dataset_homework_rows",
    "list_internal_dataset_lesson_rows",
    "list_internal_overview_attendance_rows",
    "list_internal_overview_exam_rows",
    "list_internal_overview_enrollment_rows",
    "list_internal_overview_homework_rows",
    "list_lesson_rows",
    "list_lesson_catalog_rows_by_subject",
    "list_msi_v2_table_names",
    "list_school_rows",
    "list_student_codes_with_prefix",
    "list_students_by_school_id",
    "list_subject_dashboard_rows",
    "list_subject_rows",
    "mint_legacy_id",
    "update_group_code",
    "upsert_group_student_enrollment",
    "upsert_subject",
]
