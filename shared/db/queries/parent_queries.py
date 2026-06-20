"""Parent-child assignment SQL helpers."""


def list_parent_child_rows(conn, parent_admin_id):
    return conn.execute(
        """
        SELECT
            s.id,
            s.full_name,
            s.student_id,
            s.password,
            s.subjects,
            s.telegram_user_id,
            s.photo_url,
            s.profile_description,
            s.class_name,
            s.school_name,
            s.last_seen_at,
            pc.assigned_at
        FROM parent_children pc
        JOIN students s ON s.id = pc.student_row_id
        WHERE pc.parent_admin_id = %s
        ORDER BY lower(s.full_name) ASC, s.id ASC
        """,
        (int(parent_admin_id),),
    ).fetchall()


def list_parent_subject_indicator_rows(conn, student_row_id, full_name=""):
    return conn.execute(
        """
        SELECT
            e.id AS enrollment_id,
            sub.name AS subject_name,
            sub.short_name AS subject_short,
            g.name AS group_name,
            e.average_grade,
            e.coins AS total_coins,
            e.updated_at,
            COALESCE(hw.average_homework, 0) AS homework_average,
            COALESCE(att.present_count, 0) AS present_count,
            COALESCE(att.absent_count, 0) AS absent_count,
            COALESCE(att.justified_count, 0) AS justified_count,
            COALESCE(ex.exam_average, 0) AS exam_average,
            COALESCE(progress.completed_lessons, 0) AS program_completed_lessons
        FROM academic_enrollments e
        JOIN academic_subjects sub ON sub.id = e.subject_id
        JOIN academic_groups g ON g.id = e.group_id
        LEFT JOIN (
            SELECT enrollment_id, AVG(score) AS average_homework
            FROM academic_homework_scores
            GROUP BY enrollment_id
        ) hw ON hw.enrollment_id = e.id
        LEFT JOIN (
            SELECT
                enrollment_id,
                SUM(CASE WHEN lower(status) = 'present' THEN 1 ELSE 0 END) AS present_count,
                SUM(CASE WHEN lower(status) = 'absent' THEN 1 ELSE 0 END) AS absent_count,
                SUM(CASE WHEN lower(status) IN ('justified', 'justified absent') THEN 1 ELSE 0 END) AS justified_count
            FROM academic_attendance_records
            WHERE trim(COALESCE(status, '')) <> ''
            GROUP BY enrollment_id
        ) att ON att.enrollment_id = e.id
        LEFT JOIN (
            SELECT enrollment_id, AVG(score) AS exam_average
            FROM academic_exam_results
            GROUP BY enrollment_id
        ) ex ON ex.enrollment_id = e.id
        LEFT JOIN (
            SELECT enrollment_id, MAX(lesson_order) AS completed_lessons
            FROM academic_attendance_records
            WHERE trim(COALESCE(status, '')) <> ''
            GROUP BY enrollment_id
        ) progress ON progress.enrollment_id = e.id
        WHERE (
            e.student_row_id = %s
            OR lower(trim(e.full_name)) = lower(trim(%s))
        )
          AND e.active = 1
          AND e.enrollment_status = 'active'
          AND lower(g.name) <> 'online'
        ORDER BY lower(sub.name) ASC, lower(g.name) ASC, e.id ASC
        """,
        (int(student_row_id), str(full_name or "").strip()),
    ).fetchall()


def list_parent_recent_lesson_rows(conn, student_row_id, full_name="", limit=24):
    normalized_limit = max(1, min(int(limit or 24), 300))
    return conn.execute(
        """
        SELECT
            sub.name AS subject_name,
            g.name AS group_name,
            a.lesson_label AS lesson_number,
            a.topic AS lesson_topic,
            a.lesson_date,
            a.lesson_order,
            a.status AS attendance_status,
            a.updated_at,
            'attendance' AS source
        FROM academic_attendance_records a
        JOIN academic_enrollments e ON e.id = a.enrollment_id
        JOIN academic_subjects sub ON sub.id = e.subject_id
        JOIN academic_groups g ON g.id = e.group_id
        WHERE (
            e.student_row_id = %s
            OR lower(trim(e.full_name)) = lower(trim(%s))
        )
          AND e.active = 1
          AND e.enrollment_status = 'active'
          AND lower(g.name) <> 'online'
          AND trim(COALESCE(a.lesson_date, '')) <> ''
          AND trim(COALESCE(a.status, '')) <> ''
        ORDER BY lesson_date DESC, lesson_order DESC, updated_at DESC
        LIMIT %s
        """,
        (
            int(student_row_id),
            str(full_name or "").strip(),
            normalized_limit,
        ),
    ).fetchall()


def get_parent_child_row(conn, parent_admin_id, student_row_id):
    return conn.execute(
        """
        SELECT parent_admin_id, student_row_id, assigned_at
        FROM parent_children
        WHERE parent_admin_id = %s
          AND student_row_id = %s
        """,
        (int(parent_admin_id), int(student_row_id)),
    ).fetchone()


def insert_parent_child_row(conn, parent_admin_id, student_row_id, assigned_at):
    conn.execute(
        """
        INSERT INTO parent_children (parent_admin_id, student_row_id, assigned_at)
        VALUES (%s, %s, %s)
        ON CONFLICT (parent_admin_id, student_row_id) DO NOTHING
        """,
        (int(parent_admin_id), int(student_row_id), assigned_at),
    )


def delete_parent_child_row(conn, parent_admin_id, student_row_id):
    deleted = conn.execute(
        """
        DELETE FROM parent_children
        WHERE parent_admin_id = %s
          AND student_row_id = %s
        """,
        (int(parent_admin_id), int(student_row_id)),
    )
    return int(deleted.rowcount or 0)


__all__ = [
    "list_parent_child_rows",
    "list_parent_subject_indicator_rows",
    "list_parent_recent_lesson_rows",
    "get_parent_child_row",
    "insert_parent_child_row",
    "delete_parent_child_row",
]
