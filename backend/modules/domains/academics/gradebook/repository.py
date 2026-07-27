"""Gradebook persistence and read queries."""


_GROUP_MATCH = "(g.legacy_group_id = %s OR (g.legacy_group_id IS NULL AND g.id = %s))"


def get_group_header(conn, group_id):
    return conn.execute(
        f"""
        SELECT g.id, g.legacy_group_id, g.school_id, g.group_name, g.group_code,
               s.school_key, subj.subject_name,
               (SELECT count(*) FROM (
                  SELECT lower(btrim(exam_item.title)) AS exam_key
                  FROM msi_v2.subject_program_items exam_item
                  WHERE exam_item.program_id = g.program_id AND exam_item.item_type = 'exam'
                  UNION
                  SELECT lower(btrim(result.exam_name)) AS exam_key
                  FROM msi_v2.exam_results result
                  WHERE result.group_id = g.id AND btrim(result.exam_name) <> ''
                ) known_exams) AS exam_count
        FROM msi_v2.groups g
        JOIN msi_v2.schools s ON s.id = g.school_id
        JOIN msi_v2.subject_programs sp ON sp.id = g.program_id
        JOIN msi_v2.subjects subj ON subj.id = sp.subject_id
        WHERE {_GROUP_MATCH}
          AND g.status = 'active'
        """,
        (int(group_id), int(group_id)),
    ).fetchone()


def list_primary_lesson_rows(conn, group_id):
    return conn.execute(
        """
        WITH ranked_sessions AS (
            SELECT ls.id,
                   ls.program_item_id,
                   COALESCE(NULLIF(ls.source_label, ''), spi.lesson_number, 'Session') AS lesson_number,
                   COALESCE(NULLIF(ls.source_topic, ''), spi.title, '') AS topic,
                   COALESCE(to_char(ls.session_date, 'DD/MM/YYYY'), '') AS lesson_date,
                   ls.session_date,
                   COALESCE(to_char(ls.start_time, 'HH24:MI'), '') AS start_time,
                   COALESCE(to_char(ls.end_time, 'HH24:MI'), '') AS end_time,
                   COALESCE(ls.room, '') AS room,
                   COALESCE(NULLIF(ls.source_order, 0), spi.item_order, 999999) AS lesson_order,
                   ls.status,
                   COALESCE(NULLIF(ls.source_kind, ''), spi.item_type, 'session') AS source_kind,
                   CASE
                     WHEN COALESCE(NULLIF(ls.source_kind, ''), spi.item_type, '') = 'lesson' THEN true
                     WHEN ls.program_item_id IS NOT NULL AND spi.item_type = 'lesson' THEN true
                     ELSE false
                   END AS has_homework,
                   (EXISTS (SELECT 1 FROM msi_v2.attendance_records ar
                            WHERE ar.lesson_session_id=ls.id)
                    OR EXISTS (SELECT 1 FROM msi_v2.homework_scores hw
                               WHERE hw.lesson_session_id=ls.id)) AS has_academic_records,
                   ROW_NUMBER() OVER (
                     PARTITION BY COALESCE(ls.program_item_id, -ls.id)
                     ORDER BY CASE WHEN ls.source_key <> '' THEN 0 ELSE 1 END,
                              COALESCE(NULLIF(ls.source_order, 0), spi.item_order, 999999),
                              ls.session_date NULLS LAST,
                              ls.id
                   ) AS session_rank
            FROM msi_v2.lesson_sessions ls
            LEFT JOIN msi_v2.subject_program_items spi ON spi.id = ls.program_item_id
            WHERE ls.group_id = %s
              AND (
                spi.item_type = 'lesson'
                OR (ls.program_item_id IS NULL AND ls.source_key <> '')
              )
        )
        SELECT ls.id,
               ls.lesson_number,
               ls.topic,
               ls.lesson_date,
               ls.start_time,
               ls.end_time,
               ls.room,
               ls.lesson_order,
               ls.status,
               ls.source_kind,
               ls.has_homework,
               ls.has_academic_records
        FROM ranked_sessions ls
        WHERE ls.session_rank = 1
        ORDER BY ls.lesson_order,
                 ls.session_date NULLS LAST,
                 ls.id
        """,
        (int(group_id),),
    ).fetchall()


def list_active_cancellation_rows(conn, group_id):
    return conn.execute(
        """
        SELECT e.id, e.lesson_session_id,
               COALESCE(NULLIF(ls.source_label, ''), spi.lesson_number, 'Lesson') AS lesson_number,
               to_char(e.original_session_date, 'DD/MM/YYYY') AS lesson_date,
               COALESCE(to_char(e.original_start_time, 'HH24:MI'), '') AS start_time,
               COALESCE(to_char(e.original_end_time, 'HH24:MI'), '') AS end_time,
               COALESCE(ls.room, '') AS room,
               COALESCE(NULLIF(ls.source_order, 0), spi.item_order, 999999) AS lesson_order,
               e.reason
        FROM msi_v2.lesson_schedule_exceptions e
        JOIN msi_v2.lesson_sessions ls ON ls.id=e.lesson_session_id
        LEFT JOIN msi_v2.subject_program_items spi ON spi.id=ls.program_item_id
        WHERE e.group_id=%s AND e.status='cancelled'
        ORDER BY e.original_session_date, e.id
        """,
        (int(group_id),),
    ).fetchall()


def list_group_enrollment_rows(conn, group_id):
    return conn.execute(
        """
        SELECT gs.group_id, gs.student_id, gs.legacy_enrollment_id,
               s.legacy_public_dashboard_id, s.full_name, gs.enrollment_status,
               gs.disqualification_reason,
               COALESCE(to_char(gs.disqualified_at, 'YYYY-MM-DD"T"HH24:MI:SS"Z"'), '') AS disqualified_at,
               COALESCE(hw.average_grade, 0) AS average_grade,
               COALESCE(coins.total_coins, 0) AS coins
        FROM msi_v2.group_students gs
        JOIN msi_v2.students s ON s.id = gs.student_id
        LEFT JOIN (
            SELECT group_id, student_id, round(avg(score)::numeric, 1) AS average_grade
            FROM msi_v2.homework_scores
            WHERE group_id = %s
            GROUP BY group_id, student_id
        ) hw ON hw.group_id = gs.group_id AND hw.student_id = gs.student_id
        LEFT JOIN (
            SELECT student_id, sum(amount)::int AS total_coins
            FROM msi_v2.coin_events
            WHERE group_id = %s
            GROUP BY student_id
        ) coins ON coins.student_id = gs.student_id
        WHERE gs.group_id = %s
        ORDER BY
          CASE gs.enrollment_status
            WHEN 'active' THEN 0
            WHEN 'disqualified' THEN 1
            WHEN 'banned' THEN 2
            ELSE 3
          END,
          s.full_name
        """,
        (int(group_id), int(group_id), int(group_id)),
    ).fetchall()


def list_attendance_rows(conn, enrollment_ids, lesson_session_ids):
    if not enrollment_ids or not lesson_session_ids:
        return []
    enrollment_placeholders = ",".join(["%s"] * len(enrollment_ids))
    lesson_placeholders = ",".join(["%s"] * len(lesson_session_ids))
    return conn.execute(
        f"""
        SELECT gs.legacy_enrollment_id AS enrollment_id, ls.id AS lesson_session_id,
               COALESCE(NULLIF(ls.source_label, ''), spi.lesson_number, '') AS lesson_label,
               ar.attendance_status AS status
        FROM msi_v2.attendance_records ar
        JOIN msi_v2.group_students gs
             ON gs.group_id = ar.group_id AND gs.student_id = ar.student_id
        JOIN msi_v2.lesson_sessions ls ON ls.id = ar.lesson_session_id
        LEFT JOIN msi_v2.subject_program_items spi ON spi.id = ls.program_item_id
        WHERE gs.legacy_enrollment_id IN ({enrollment_placeholders})
          AND ar.lesson_session_id IN ({lesson_placeholders})
          AND (
            spi.item_type = 'lesson'
            OR (ls.program_item_id IS NULL AND ls.source_key <> '')
          )
          AND COALESCE(NULLIF(ls.source_label, ''), spi.lesson_number, '') <> ''
        """,
        [*enrollment_ids, *lesson_session_ids],
    ).fetchall()


def list_homework_rows(conn, enrollment_ids, lesson_session_ids):
    if not enrollment_ids or not lesson_session_ids:
        return []
    enrollment_placeholders = ",".join(["%s"] * len(enrollment_ids))
    lesson_placeholders = ",".join(["%s"] * len(lesson_session_ids))
    return conn.execute(
        f"""
        SELECT gs.legacy_enrollment_id AS enrollment_id, ls.id AS lesson_session_id,
               COALESCE(NULLIF(ls.source_label, ''), spi.lesson_number, '') AS lesson_label,
               hw.score
        FROM msi_v2.homework_scores hw
        JOIN msi_v2.group_students gs
             ON gs.group_id = hw.group_id AND gs.student_id = hw.student_id
        JOIN msi_v2.lesson_sessions ls ON ls.id = hw.lesson_session_id
        LEFT JOIN msi_v2.subject_program_items spi ON spi.id = ls.program_item_id
        WHERE gs.legacy_enrollment_id IN ({enrollment_placeholders})
          AND hw.lesson_session_id IN ({lesson_placeholders})
          AND (
            spi.item_type = 'lesson'
            OR (ls.program_item_id IS NULL AND ls.source_key <> '')
          )
          AND COALESCE(NULLIF(ls.source_label, ''), spi.lesson_number, '') <> ''
        """,
        [*enrollment_ids, *lesson_session_ids],
    ).fetchall()


def list_exam_rows(conn, enrollment_ids):
    if not enrollment_ids:
        return []
    placeholders = ",".join(["%s"] * len(enrollment_ids))
    return conn.execute(
        f"""
        SELECT gs.legacy_enrollment_id AS enrollment_id,
               er.exam_name, er.attempt, er.score,
               COALESCE(spi.item_type, '') AS item_type,
               COALESCE(spi.title, '') AS item_title,
               COALESCE(
                 to_char(exam_session.session_date, 'DD/MM/YYYY'),
                 to_char(er.created_at, 'DD/MM/YYYY'),
                 ''
               ) AS exam_date
        FROM msi_v2.exam_results er
        JOIN msi_v2.group_students gs
             ON gs.group_id = er.group_id AND gs.student_id = er.student_id
        LEFT JOIN msi_v2.subject_program_items spi ON spi.id = er.program_item_id
        LEFT JOIN LATERAL (
            SELECT ls.session_date
            FROM msi_v2.lesson_sessions ls
            WHERE ls.group_id = er.group_id
              AND ls.program_item_id = er.program_item_id
            ORDER BY ls.session_date NULLS LAST, ls.id
            LIMIT 1
        ) exam_session ON TRUE
        WHERE gs.legacy_enrollment_id IN ({placeholders})
        ORDER BY er.exam_name, er.attempt
        """,
        enrollment_ids,
    ).fetchall()


def get_enrollment_metrics(conn, *, group_id, student_id):
    return conn.execute(
        """
        SELECT
          (SELECT COALESCE(round(avg(hw.score)::numeric, 1), 0)
           FROM msi_v2.homework_scores hw
           WHERE hw.group_id = %s AND hw.student_id = %s) AS average_grade,
          (SELECT count(*)
           FROM msi_v2.attendance_records ar
           WHERE ar.group_id = %s AND ar.student_id = %s
             AND ar.attendance_status IN ('present', 'absent', 'justified')) AS attendance_total,
          (SELECT count(*)
           FROM msi_v2.attendance_records ar
           WHERE ar.group_id = %s AND ar.student_id = %s
             AND ar.attendance_status = 'present') AS attendance_present
        """,
        (
            int(group_id), int(student_id),
            int(group_id), int(student_id),
            int(group_id), int(student_id),
        ),
    ).fetchone()


def get_active_group_identity(conn, group_id):
    return conn.execute(
        f"""
        SELECT g.id, g.school_id
        FROM msi_v2.groups g
        WHERE {_GROUP_MATCH}
          AND g.status = 'active'
        """,
        (int(group_id), int(group_id)),
    ).fetchone()


def list_monthly_trend_rows(
    conn, *, group_id, school_id, start_month, through_month, end_month
):
    return conn.execute(
        """
        WITH calendar_months AS (
            SELECT generate_series(%s::date, %s::date, interval '1 month')::date AS month_start
        ),
        closure_months AS (
            SELECT months.month_start,
                   COALESCE(
                     array_agg(DISTINCT closure.title ORDER BY closure.title)
                       FILTER (WHERE closure.id IS NOT NULL),
                     ARRAY[]::text[]
                   ) AS closure_titles
            FROM calendar_months months
            LEFT JOIN msi_v2.academic_calendar_closures closure
              ON closure.school_id = %s
             AND closure.status = 'active'
             AND (closure.group_id IS NULL OR closure.group_id = %s)
             AND closure.start_date < (months.month_start + interval '1 month')::date
             AND closure.end_date >= months.month_start
            GROUP BY months.month_start
        ),
        active_students AS (
            SELECT gs.student_id
            FROM msi_v2.group_students gs
            WHERE gs.group_id = %s
              AND gs.enrollment_status = 'active'
        ),
        ranked_sessions AS (
            SELECT ls.id,
                   ls.session_date,
                   ROW_NUMBER() OVER (
                     PARTITION BY COALESCE(ls.program_item_id, -ls.id)
                     ORDER BY CASE WHEN ls.source_key <> '' THEN 0 ELSE 1 END,
                              COALESCE(NULLIF(ls.source_order, 0), spi.item_order, 999999),
                              ls.session_date NULLS LAST,
                              ls.id
                   ) AS session_rank
            FROM msi_v2.lesson_sessions ls
            LEFT JOIN msi_v2.subject_program_items spi ON spi.id = ls.program_item_id
            WHERE ls.group_id = %s
              AND (
                spi.item_type = 'lesson'
                OR (ls.program_item_id IS NULL AND ls.source_key <> '')
              )
        ),
        month_lessons AS (
            SELECT rs.id,
                   date_trunc('month', rs.session_date)::date AS month_start
            FROM ranked_sessions rs
            WHERE rs.session_rank = 1
              AND rs.session_date >= %s
              AND rs.session_date < %s
        ),
        lesson_counts AS (
            SELECT ml.month_start, count(*)::int AS lesson_count
            FROM month_lessons ml
            GROUP BY ml.month_start
        ),
        homework_by_student AS (
            SELECT ml.month_start,
                   active.student_id,
                   round(avg(hw.score)::numeric, 1) AS avg_aap,
                   count(*)::int AS homework_record_count
            FROM active_students active
            JOIN msi_v2.homework_scores hw
              ON hw.group_id = %s AND hw.student_id = active.student_id
            JOIN month_lessons ml ON ml.id = hw.lesson_session_id
            WHERE hw.score > 0
            GROUP BY ml.month_start, active.student_id
        ),
        attendance_by_student AS (
            SELECT ml.month_start,
                   active.student_id,
                   round(
                     count(*) FILTER (WHERE ar.attendance_status = 'present') * 100.0
                     / NULLIF(count(*), 0),
                     0
                   ) AS avg_ar,
                   count(*)::int AS attendance_record_count
            FROM active_students active
            JOIN msi_v2.attendance_records ar
              ON ar.group_id = %s AND ar.student_id = active.student_id
            JOIN month_lessons ml ON ml.id = ar.lesson_session_id
            WHERE ar.attendance_status IN ('present', 'absent', 'justified')
            GROUP BY ml.month_start, active.student_id
        ),
        student_months AS (
            SELECT COALESCE(hw.month_start, ar.month_start) AS month_start,
                   COALESCE(hw.student_id, ar.student_id) AS student_id,
                   hw.avg_aap,
                   ar.avg_ar,
                   COALESCE(hw.homework_record_count, 0) AS homework_record_count,
                   COALESCE(ar.attendance_record_count, 0) AS attendance_record_count
            FROM homework_by_student hw
            FULL OUTER JOIN attendance_by_student ar
              ON ar.month_start = hw.month_start AND ar.student_id = hw.student_id
        ),
        student_scores AS (
            SELECT sm.*,
                   CASE
                     WHEN sm.avg_aap IS NULL AND sm.avg_ar IS NULL THEN NULL
                     WHEN sm.avg_aap IS NULL THEN round((sm.avg_ar * 9.0 / 100.0)::numeric, 1)
                     WHEN sm.avg_ar IS NULL THEN sm.avg_aap
                     ELSE round(
                       (sm.avg_aap + round((sm.avg_ar * 9.0 / 100.0)::numeric, 1)) / 2.0,
                       1
                     )
                   END AS avg_performance
            FROM student_months sm
        ),
        monthly_metrics AS (
            SELECT scores.month_start,
                   round(avg(scores.avg_aap)::numeric, 1) AS avg_aap,
                   round(avg(scores.avg_ar)::numeric, 1) AS avg_ar,
                   round(avg(scores.avg_performance)::numeric, 1) AS avg_performance,
                   count(*)::int AS students_with_data,
                   sum(scores.homework_record_count)::int AS homework_record_count,
                   sum(scores.attendance_record_count)::int AS attendance_record_count
            FROM student_scores scores
            GROUP BY scores.month_start
        )
        SELECT months.month_start,
               metrics.avg_aap,
               metrics.avg_ar,
               metrics.avg_performance,
               COALESCE(lessons.lesson_count, 0)::int AS lesson_count,
               COALESCE(metrics.students_with_data, 0)::int AS students_with_data,
               COALESCE(metrics.homework_record_count, 0)::int AS homework_record_count,
               COALESCE(metrics.attendance_record_count, 0)::int AS attendance_record_count,
               closures.closure_titles
        FROM calendar_months months
        LEFT JOIN monthly_metrics metrics ON metrics.month_start = months.month_start
        LEFT JOIN lesson_counts lessons ON lessons.month_start = months.month_start
        JOIN closure_months closures ON closures.month_start = months.month_start
        ORDER BY months.month_start
        """,
        (
            start_month,
            through_month,
            int(school_id),
            int(group_id),
            int(group_id),
            int(group_id),
            start_month,
            end_month,
            int(group_id),
            int(group_id),
        ),
    ).fetchall()


def upsert_homework_score(
    conn,
    *,
    lesson_session_id,
    group_id,
    student_id,
    score,
    actor_staff_id,
    recorded_at,
):
    return conn.execute(
        """
        INSERT INTO msi_v2.homework_scores (
            lesson_session_id, group_id, student_id, score, score_scale,
            recorded_by_staff_id, created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, 9, %s, %s, %s)
        ON CONFLICT (lesson_session_id, student_id) DO UPDATE SET
            score = excluded.score,
            recorded_by_staff_id = excluded.recorded_by_staff_id,
            updated_at = excluded.updated_at
        RETURNING id
        """,
        (
            int(lesson_session_id), int(group_id), int(student_id), score,
            int(actor_staff_id) if actor_staff_id else None, recorded_at, recorded_at,
        ),
    ).fetchone()


def insert_coin_event(conn, *, student_id, group_id, amount, source, occurred_at):
    return conn.execute(
        """
        INSERT INTO msi_v2.coin_events (
            student_id, group_id, amount, source, note, occurred_at, created_at
        )
        VALUES (%s, %s, %s, %s, '', %s, %s)
        RETURNING id
        """,
        (int(student_id), int(group_id), int(amount), source, occurred_at, occurred_at),
    ).fetchone()


__all__ = ["insert_coin_event", "upsert_homework_score"]
