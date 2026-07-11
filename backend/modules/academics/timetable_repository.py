"""Timetable SQL helpers for schedule rules and lesson sessions.

DB-5 owns timetable query access here while the physical database schema remains
``msi_v2``.
"""


def list_schedule_rows(conn):
    return conn.execute(
        """
        SELECT sch.id, g.school_id, s.school_key AS school_code, s.school_name,
               subj.id AS subject_id, subj.subject_name,
               coalesce(g.legacy_group_id, g.id) AS group_id, g.group_name,
               coalesce(t.legacy_teacher_id, t.id) AS teacher_id,
               coalesce(t.full_name, '') AS teacher_name,
               sch.title, sch.weekdays,
               coalesce(to_char(sch.start_time, 'HH24:MI'), '') AS start_time,
               coalesce(to_char(sch.end_time, 'HH24:MI'), '') AS end_time,
               coalesce(to_char(sch.start_date, 'DD/MM/YYYY'), '') AS start_date,
               coalesce(to_char(sch.end_date, 'DD/MM/YYYY'), '') AS end_date,
               sch.room, sch.online_url, sch.status
        FROM msi_v2.group_schedule_rules sch
        JOIN msi_v2.groups g ON g.id = sch.group_id
        JOIN msi_v2.schools s ON s.id = g.school_id
        JOIN msi_v2.subject_programs sp ON sp.id = g.program_id
        JOIN msi_v2.subjects subj ON subj.id = sp.subject_id
        LEFT JOIN msi_v2.teachers t ON t.id = sch.teacher_id
        WHERE lower(g.group_name) <> 'online'
        ORDER BY s.school_name, subj.subject_name, g.group_name, sch.start_time
        """
    ).fetchall()


def list_session_rows(conn):
    return conn.execute(
        """
        SELECT ls.id, ls.schedule_rule_id AS schedule_id, ls.program_item_id AS lesson_id,
               g.school_id, s.school_key AS school_code, s.school_name,
               subj.id AS subject_id, subj.subject_name,
               coalesce(g.legacy_group_id, g.id) AS group_id, g.group_name,
               coalesce(t.legacy_teacher_id, t.id) AS teacher_id,
               coalesce(t.full_name, '') AS teacher_name,
               coalesce(to_char(ls.session_date, 'DD/MM/YYYY'), '') AS session_date,
               coalesce(to_char(ls.start_time, 'HH24:MI'), '') AS start_time,
               coalesce(to_char(ls.end_time, 'HH24:MI'), '') AS end_time,
               ls.room, ls.online_url, ls.status
        FROM msi_v2.lesson_sessions ls
        JOIN msi_v2.groups g ON g.id = ls.group_id
        JOIN msi_v2.schools s ON s.id = g.school_id
        JOIN msi_v2.subject_programs sp ON sp.id = g.program_id
        JOIN msi_v2.subjects subj ON subj.id = sp.subject_id
        LEFT JOIN msi_v2.teachers t ON t.id = ls.teacher_id
        WHERE (ls.schedule_rule_id IS NOT NULL
               OR (ls.start_time IS NOT NULL AND ls.end_time IS NOT NULL))
          AND lower(g.group_name) <> 'online'
        ORDER BY ls.session_date, ls.start_time, s.school_name, g.group_name
        """
    ).fetchall()


def list_schedule_conflict_rows(conn, group_v2_id, teacher_v2_id, exclude_schedule_id=0):
    return conn.execute(
        """
        SELECT sch.id, sch.group_id, sch.teacher_id, sch.weekdays,
               to_char(sch.start_date, 'DD/MM/YYYY') AS start_date,
               to_char(sch.end_date, 'DD/MM/YYYY') AS end_date,
               to_char(sch.start_time, 'HH24:MI') AS start_time,
               to_char(sch.end_time, 'HH24:MI') AS end_time,
               g.group_name AS group_name,
               coalesce(t.full_name, '') AS teacher_name
        FROM msi_v2.group_schedule_rules sch
        JOIN msi_v2.groups g ON g.id = sch.group_id
        LEFT JOIN msi_v2.teachers t ON t.id = sch.teacher_id
        WHERE sch.status = 'active'
          AND (sch.group_id = %s OR (%s > 0 AND sch.teacher_id = %s))
          AND sch.id <> %s
        """,
        (int(group_v2_id), int(teacher_v2_id or 0), int(teacher_v2_id or 0), int(exclude_schedule_id or 0)),
    ).fetchall()


def get_active_group_schedule(conn, group_v2_id):
    return conn.execute(
        """SELECT id, group_id, teacher_id, title, weekdays,
                  to_char(start_time, 'HH24:MI') AS start_time,
                  to_char(end_time, 'HH24:MI') AS end_time,
                  start_date, end_date, room, online_url
           FROM msi_v2.group_schedule_rules
           WHERE group_id = %s AND status = 'active'
           ORDER BY id DESC LIMIT 1""",
        (int(group_v2_id),),
    ).fetchone()


def update_schedule_rule(conn, schedule_id, **values):
    conn.execute(
        """UPDATE msi_v2.group_schedule_rules SET
             teacher_id=%s, title=%s, weekdays=%s, start_time=%s, end_time=%s,
             start_date=%s, end_date=%s, room=%s, online_url=%s, updated_at=now()
           WHERE id=%s""",
        (values["teacher_v2_id"] or None, values["title"], values["weekdays_text"],
         values["start_time"], values["end_time"], values["start_date"], values["end_date"],
         values["room"], values["online_url"], int(schedule_id)),
    )


def delete_unrecorded_schedule_sessions(conn, schedule_id):
    conn.execute(
        """DELETE FROM msi_v2.lesson_sessions ls
           WHERE ls.schedule_rule_id = %s AND ls.status = 'scheduled'
             AND NOT EXISTS (SELECT 1 FROM msi_v2.attendance_records ar WHERE ar.lesson_session_id=ls.id)
             AND NOT EXISTS (SELECT 1 FROM msi_v2.homework_scores hw WHERE hw.lesson_session_id=ls.id)""",
        (int(schedule_id),),
    )


def ensure_curriculum_lesson_sessions(conn, group_v2_id):
    conn.execute(
        """INSERT INTO msi_v2.lesson_sessions (
             group_id, program_item_id, status, source_key, source_kind,
             source_label, source_topic, source_order, source_file, source_sheet,
             created_at, updated_at
           )
           SELECT g.id, spi.id, 'scheduled', concat('curriculum:', g.id, ':', spi.id),
                  'lesson', spi.lesson_number, spi.title, spi.item_order,
                  spi.source_file, spi.sheet_name, now(), now()
           FROM msi_v2.groups g
           JOIN msi_v2.subject_program_items spi ON spi.program_id=g.program_id
           WHERE g.id=%s AND spi.item_type='lesson'
             AND NOT EXISTS (SELECT 1 FROM msi_v2.lesson_sessions ls
                             WHERE ls.group_id=g.id AND ls.program_item_id=spi.id)
           ON CONFLICT (source_key) WHERE source_key <> '' DO NOTHING""",
        (int(group_v2_id),),
    )


def list_curriculum_lesson_sessions(conn, group_v2_id):
    return conn.execute(
        """SELECT ls.id, ls.status, ls.session_date, spi.item_order
           FROM msi_v2.lesson_sessions ls
           JOIN msi_v2.subject_program_items spi ON spi.id=ls.program_item_id
           WHERE ls.group_id=%s AND spi.item_type='lesson'
           ORDER BY spi.item_order, ls.id""",
        (int(group_v2_id),),
    ).fetchall()


def schedule_curriculum_lesson(conn, lesson_session_id, *, schedule_id, teacher_v2_id,
                               session_date, start_time, end_time, room):
    conn.execute(
        """UPDATE msi_v2.lesson_sessions SET schedule_rule_id=%s, teacher_id=%s,
             session_date=%s, start_time=%s, end_time=%s, room=%s, updated_at=now()
           WHERE id=%s""",
        (int(schedule_id), int(teacher_v2_id) or None, session_date, start_time,
         end_time, room, int(lesson_session_id)),
    )


def cancel_schedule_rule(conn, schedule_id):
    conn.execute(
        "UPDATE msi_v2.group_schedule_rules SET status='cancelled', updated_at=now() WHERE id=%s",
        (int(schedule_id),),
    )


def delete_unrecorded_generic_group_sessions(conn, group_v2_id):
    conn.execute(
        """DELETE FROM msi_v2.lesson_sessions ls
           WHERE ls.group_id=%s AND ls.program_item_id IS NULL AND ls.status='scheduled'
             AND NOT EXISTS (SELECT 1 FROM msi_v2.attendance_records ar WHERE ar.lesson_session_id=ls.id)
             AND NOT EXISTS (SELECT 1 FROM msi_v2.homework_scores hw WHERE hw.lesson_session_id=ls.id)""",
        (int(group_v2_id),),
    )


def insert_schedule_rule(
    conn,
    *,
    group_v2_id,
    teacher_v2_id,
    title,
    weekdays_text,
    start_time,
    end_time,
    start_date,
    end_date,
    room,
    online_url,
):
    return conn.execute(
        """
        INSERT INTO msi_v2.group_schedule_rules (
          group_id, teacher_id, title, weekdays, start_time, end_time,
          start_date, end_date, room, online_url, status
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'active')
        RETURNING id
        """,
        (
            int(group_v2_id),
            int(teacher_v2_id) or None,
            title,
            weekdays_text,
            start_time,
            end_time,
            start_date,
            end_date,
            room,
            online_url,
        ),
    ).fetchone()


def insert_lesson_session(
    conn,
    *,
    group_v2_id,
    schedule_id,
    teacher_v2_id,
    session_date,
    start_time,
    end_time,
    room,
    online_url,
):
    return conn.execute(
        """
        INSERT INTO msi_v2.lesson_sessions (
          group_id, schedule_rule_id, teacher_id, session_date,
          start_time, end_time, room, online_url, status
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'scheduled')
        RETURNING id
        """,
        (
            int(group_v2_id),
            int(schedule_id),
            int(teacher_v2_id) or None,
            session_date,
            start_time,
            end_time,
            room,
            online_url,
        ),
    ).fetchone()


__all__ = [
    "insert_lesson_session",
    "insert_schedule_rule",
    "list_schedule_conflict_rows",
    "list_schedule_rows",
    "get_active_group_schedule",
    "update_schedule_rule",
    "delete_unrecorded_schedule_sessions",
    "ensure_curriculum_lesson_sessions",
    "list_curriculum_lesson_sessions",
    "schedule_curriculum_lesson",
    "cancel_schedule_rule",
    "delete_unrecorded_generic_group_sessions",
    "list_session_rows",
]
