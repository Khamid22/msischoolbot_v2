"""PostgreSQL access for school and group academic calendar closures."""

from __future__ import annotations


def get_school(conn, school_id):
    return conn.execute(
        "SELECT id, school_key, school_name FROM msi_v2.schools WHERE id=%s",
        (int(school_id),),
    ).fetchone()


def list_scope_groups(conn, school_id, group_v2_id=0):
    params = [int(school_id)]
    group_filter = ""
    if int(group_v2_id or 0) > 0:
        group_filter = " AND g.id=%s"
        params.append(int(group_v2_id))
    return conn.execute(
        f"""SELECT g.id, coalesce(g.legacy_group_id, g.id) AS public_group_id,
                   g.group_name, g.school_id
            FROM msi_v2.groups g
            WHERE g.school_id=%s AND g.status='active'
              {group_filter}
            ORDER BY g.id""",
        params,
    ).fetchall()


def list_calendar_closures(
    conn, *, school_id=0, group_v2_id=0, start_date=None, end_date=None, include_unlocked=False
):
    filters = []
    params = []
    if not include_unlocked:
        filters.append("c.status='active'")
    if int(school_id or 0) > 0:
        filters.append("c.school_id=%s")
        params.append(int(school_id))
    if int(group_v2_id or 0) > 0:
        filters.append("(c.group_id IS NULL OR c.group_id=%s)")
        params.append(int(group_v2_id))
    if start_date is not None and end_date is not None:
        filters.append("c.start_date <= %s AND %s <= c.end_date")
        params.extend([end_date, start_date])
    where = " AND ".join(filters) if filters else "TRUE"
    return conn.execute(
        f"""SELECT c.id, c.school_id, c.group_id,
                   coalesce(g.legacy_group_id, g.id) AS public_group_id,
                   s.school_key, s.school_name, coalesce(g.group_name, '') AS group_name,
                   c.title, c.start_date, c.end_date, c.status,
                   c.created_at, c.unlocked_at,
                   CASE WHEN c.group_id IS NULL THEN 'school' ELSE 'group' END AS scope
            FROM msi_v2.academic_calendar_closures c
            JOIN msi_v2.schools s ON s.id=c.school_id
            LEFT JOIN msi_v2.groups g ON g.id=c.group_id
            WHERE {where}
            ORDER BY c.start_date, c.end_date, c.id""",
        params,
    ).fetchall()


def list_effective_group_closures(conn, school_id, group_v2_id):
    return conn.execute(
        """SELECT id, school_id, group_id, title, start_date, end_date,
                  CASE WHEN group_id IS NULL THEN 'school' ELSE 'group' END AS scope
           FROM msi_v2.academic_calendar_closures
           WHERE school_id=%s AND status='active'
             AND (group_id IS NULL OR group_id=%s)
           ORDER BY start_date, end_date, id""",
        (int(school_id), int(group_v2_id)),
    ).fetchall()


def group_date_has_active_closure(conn, school_id, group_v2_id, session_date):
    return conn.execute(
        """SELECT id, title, start_date, end_date,
                  CASE WHEN group_id IS NULL THEN 'school' ELSE 'group' END AS scope
           FROM msi_v2.academic_calendar_closures
           WHERE school_id=%s AND status='active'
             AND (group_id IS NULL OR group_id=%s)
             AND start_date <= %s AND %s <= end_date
           ORDER BY CASE WHEN group_id IS NULL THEN 0 ELSE 1 END, id
           LIMIT 1""",
        (int(school_id), int(group_v2_id), session_date, session_date),
    ).fetchone()


def get_calendar_closure(conn, closure_id, *, for_update=False):
    lock = " FOR UPDATE" if for_update else ""
    return conn.execute(
        f"""SELECT id, school_id, group_id, title, start_date, end_date, status
            FROM msi_v2.academic_calendar_closures WHERE id=%s{lock}""",
        (int(closure_id),),
    ).fetchone()


def find_exact_active_closure(conn, school_id, group_v2_id, start_date, end_date):
    if int(group_v2_id or 0) > 0:
        condition = "group_id=%s"
        scope_params = [int(group_v2_id)]
    else:
        condition = "group_id IS NULL"
        scope_params = []
    return conn.execute(
        f"""SELECT id FROM msi_v2.academic_calendar_closures
            WHERE school_id=%s AND {condition} AND start_date=%s AND end_date=%s
              AND status='active' LIMIT 1""",
        [int(school_id), *scope_params, start_date, end_date],
    ).fetchone()


def lock_closure_scope(conn, school_id):
    conn.execute("SELECT pg_advisory_xact_lock(%s, %s)", (7303, int(school_id))).fetchone()


def insert_calendar_closure(
    conn, *, school_id, group_v2_id, title, start_date, end_date, actor_staff_id=None
):
    return conn.execute(
        """INSERT INTO msi_v2.academic_calendar_closures (
                 school_id, group_id, title, start_date, end_date, created_by_staff_id
             ) VALUES (%s, %s, %s, %s, %s, %s)
             RETURNING id, school_id, group_id, title, start_date, end_date, status""",
        (
            int(school_id), int(group_v2_id) or None, str(title).strip(),
            start_date, end_date, actor_staff_id,
        ),
    ).fetchone()


def unlock_calendar_closure(conn, closure_id, actor_staff_id=None):
    return conn.execute(
        """UPDATE msi_v2.academic_calendar_closures
           SET status='unlocked', unlocked_by_staff_id=%s, unlocked_at=now(), updated_at=now()
           WHERE id=%s AND status='active'
           RETURNING id, school_id, group_id, title, start_date, end_date, status""",
        (actor_staff_id, int(closure_id)),
    ).fetchone()


def list_group_curriculum_for_reflow(conn, group_v2_id):
    return conn.execute(
        """SELECT ls.id, ls.group_id, ls.schedule_rule_id, ls.teacher_id,
                  ls.session_date, ls.start_time, ls.end_time, ls.room,
                  ls.status, spi.item_order,
                  (EXISTS (SELECT 1 FROM msi_v2.attendance_records ar
                           WHERE ar.lesson_session_id=ls.id)
                   OR EXISTS (SELECT 1 FROM msi_v2.homework_scores hw
                              WHERE hw.lesson_session_id=ls.id)) AS has_academic_records
           FROM msi_v2.lesson_sessions ls
           JOIN msi_v2.subject_program_items spi ON spi.id=ls.program_item_id
           WHERE ls.group_id=%s AND spi.item_type='lesson'
           ORDER BY spi.item_order, ls.id""",
        (int(group_v2_id),),
    ).fetchall()


def max_group_curriculum_date(conn, group_v2_id):
    row = conn.execute(
        """SELECT max(ls.session_date) AS final_date
           FROM msi_v2.lesson_sessions ls
           JOIN msi_v2.subject_program_items spi ON spi.id=ls.program_item_id
           WHERE ls.group_id=%s AND spi.item_type='lesson'""",
        (int(group_v2_id),),
    ).fetchone()
    return row["final_date"] if row else None


def list_reflow_occurrence_conflicts(
    conn, *, excluded_session_ids, group_v2_id, teacher_v2_id, session_date, start_time, end_time
):
    excluded = [int(value) for value in excluded_session_ids]
    return conn.execute(
        """SELECT ls.id, ls.group_id, coalesce(g.group_name, '') AS group_name,
                  coalesce(t.full_name, '') AS teacher_name
           FROM msi_v2.lesson_sessions ls
           JOIN msi_v2.groups g ON g.id=ls.group_id
           LEFT JOIN msi_v2.teachers t ON t.id=ls.teacher_id
           WHERE NOT (ls.id = ANY(%s))
             AND ls.session_date=%s
             AND ls.start_time IS NOT NULL AND ls.end_time IS NOT NULL
             AND lower(coalesce(ls.status, 'scheduled')) NOT IN ('cancelled', 'canceled')
             AND ls.start_time < %s AND %s < ls.end_time
             AND (ls.group_id=%s OR (%s > 0 AND ls.teacher_id=%s))
           ORDER BY ls.id LIMIT 5""",
        (
            excluded, session_date, end_time, start_time, int(group_v2_id),
            int(teacher_v2_id or 0), int(teacher_v2_id or 0),
        ),
    ).fetchall()


__all__ = [
    "find_exact_active_closure",
    "get_calendar_closure",
    "get_school",
    "group_date_has_active_closure",
    "insert_calendar_closure",
    "list_calendar_closures",
    "list_effective_group_closures",
    "list_group_curriculum_for_reflow",
    "list_reflow_occurrence_conflicts",
    "list_scope_groups",
    "lock_closure_scope",
    "max_group_curriculum_date",
    "unlock_calendar_closure",
]
