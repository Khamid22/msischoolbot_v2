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


def list_schedule_conflict_rows(conn, group_v2_id, teacher_v2_id):
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
        """,
        (int(group_v2_id), int(teacher_v2_id or 0), int(teacher_v2_id or 0)),
    ).fetchall()


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
    "list_session_rows",
]
