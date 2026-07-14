"""Groups persistence for the Alembic-managed ``msi_v2`` schema."""

_GROUP_MATCH = "(g.legacy_group_id = %s OR (g.legacy_group_id IS NULL AND g.id = %s))"


def get_enrollment_by_legacy_id(conn, enrollment_id):
    return conn.execute(
        """
        SELECT gs.group_id, gs.student_id, gs.legacy_enrollment_id, gs.enrollment_status,
               g.legacy_group_id, g.id AS v2_group_id, g.school_id, g.program_id
        FROM msi_v2.group_students gs
        JOIN msi_v2.groups g ON g.id = gs.group_id
        WHERE gs.legacy_enrollment_id = %s
        """,
        (int(enrollment_id),),
    ).fetchone()


def get_active_group_by_legacy_or_id(conn, group_id):
    return conn.execute(
        """
        SELECT id, school_id, program_id
        FROM msi_v2.groups g
        WHERE (g.legacy_group_id = %s OR (g.legacy_group_id IS NULL AND g.id = %s))
          AND g.status = 'active'
        """,
        (int(group_id), int(group_id)),
    ).fetchone()


def update_enrollment_status_row(conn, *, group_id, student_id, status, reason, changed_at):
    conn.execute(
        """
        UPDATE msi_v2.group_students
        SET enrollment_status = %s,
            disqualification_reason = %s,
            disqualified_at = CASE WHEN %s = 'active' THEN NULL ELSE COALESCE(disqualified_at, %s) END,
            left_at = CASE WHEN %s = 'active' THEN NULL ELSE COALESCE(left_at, %s) END
        WHERE group_id = %s AND student_id = %s
        """,
        (status, reason, status, changed_at, status, changed_at, int(group_id), int(student_id)),
    )


def move_enrollment_row(
    conn,
    *,
    source_group_id,
    target_group_id,
    student_id,
    enrollment_status,
    joined_at,
    legacy_enrollment_id,
):
    conn.execute(
        "DELETE FROM msi_v2.group_students WHERE group_id = %s AND student_id = %s",
        (int(source_group_id), int(student_id)),
    )
    conn.execute(
        """
        INSERT INTO msi_v2.group_students (
            group_id, student_id, enrollment_status, joined_at, legacy_enrollment_id
        )
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (group_id, student_id) DO UPDATE SET
            enrollment_status = excluded.enrollment_status,
            legacy_enrollment_id = excluded.legacy_enrollment_id,
            left_at = NULL
        """,
        (
            int(target_group_id), int(student_id), str(enrollment_status or "active"),
            joined_at, int(legacy_enrollment_id),
        ),
    )

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
        WHERE {_GROUP_MATCH} AND g.status = 'active'
        """,
        (int(group_id or 0), int(group_id or 0)),
    ).fetchone()


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
        WHERE lower(g.group_name) <> 'online' AND g.status = 'active'
        GROUP BY g.id, g.legacy_group_id, g.school_id, s.school_key, s.school_name,
                 subj.id, subj.subject_name, g.class_id, c.class_name,
                 g.group_name, g.group_code, g.set_name
        ORDER BY s.school_name, subj.subject_name, g.group_name
        """
    ).fetchall()


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
        WHERE lower(g.group_name) <> 'online' AND g.status = 'active'
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
        WHERE lower(g.group_name) <> 'online' AND g.status = 'active'
        """
    ).fetchone()


def list_group_rows_page(
    conn,
    *,
    school_id=0,
    subject_id=0,
    query="",
    offset=0,
    limit=50,
):
    filters = ["lower(g.group_name) <> 'online'", "g.status = 'active'"]
    params = []
    if int(school_id or 0) > 0:
        filters.append("g.school_id = %s")
        params.append(int(school_id))
    if int(subject_id or 0) > 0:
        filters.append("subj.id = %s")
        params.append(int(subject_id))
    normalized_query = str(query or "").strip()
    if normalized_query:
        filters.append(
            "(g.group_name ILIKE %s OR g.group_code ILIKE %s "
            "OR s.school_name ILIKE %s OR subj.subject_name ILIKE %s)"
        )
        pattern = f"%{normalized_query}%"
        params.extend([pattern, pattern, pattern, pattern])
    where_sql = " AND ".join(filters)
    params.extend([int(limit), int(offset)])
    return conn.execute(
        f"""
        WITH group_rows AS (
          SELECT coalesce(g.legacy_group_id, g.id) AS id,
                 g.school_id, s.school_key AS school_code, s.school_name,
                 subj.id AS subject_id, subj.subject_name,
                 g.class_id, c.class_name, g.group_name AS name,
                 g.group_code AS code, g.set_name,
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
          WHERE {where_sql}
          GROUP BY g.id, g.legacy_group_id, g.school_id, s.school_key, s.school_name,
                   subj.id, subj.subject_name, g.class_id, c.class_name,
                   g.group_name, g.group_code, g.set_name
        )
        SELECT group_rows.*, count(*) OVER () AS filtered_total
        FROM group_rows
        ORDER BY school_name, subject_name, name, id
        LIMIT %s OFFSET %s
        """,
        params,
    ).fetchall()


def get_group_summary_row(conn, group_id):
    return conn.execute(
        f"""
        SELECT coalesce(g.legacy_group_id, g.id) AS id,
               g.group_name AS name, g.group_code AS code, g.status,
               g.school_id, s.school_key AS school_code, s.school_name,
               subj.id AS subject_id, subj.subject_name,
               g.class_id, c.class_name, g.set_name,
               (SELECT count(*) FROM msi_v2.group_students gs
                WHERE gs.group_id = g.id
                  AND gs.enrollment_status = 'active') AS students_count,
               (SELECT count(*) FROM msi_v2.lesson_sessions ls
                WHERE ls.group_id = g.id) AS lesson_count,
               (SELECT count(*) FROM msi_v2.exam_results er
                WHERE er.group_id = g.id) AS exam_result_count,
               EXISTS (
                 SELECT 1 FROM msi_v2.group_schedule_rules rule
                 WHERE rule.group_id = g.id AND rule.status = 'active'
               ) AS has_active_schedule
        FROM msi_v2.groups g
        JOIN msi_v2.schools s ON s.id = g.school_id
        LEFT JOIN msi_v2.classes c ON c.id = g.class_id
        JOIN msi_v2.subject_programs sp ON sp.id = g.program_id
        JOIN msi_v2.subjects subj ON subj.id = sp.subject_id
        WHERE {_GROUP_MATCH} AND g.status = 'active'
        """,
        (int(group_id), int(group_id)),
    ).fetchone()


def get_existing_group(conn, school_id, program_id, group_name):
    return conn.execute(
        """
        SELECT id FROM msi_v2.groups
        WHERE school_id = %s AND program_id = %s AND lower(group_name) = lower(%s)
          AND status = 'active'
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
          AND g.status = 'active'
          AND lower(s.school_key) = lower(%s)
        LIMIT 1
        """,
        (group_name, school_code),
    ).fetchone() is not None


def get_group_archive_candidate(conn, group_id):
    return conn.execute(
        f"""
        SELECT g.id, coalesce(g.legacy_group_id, g.id) AS public_id,
               g.group_name, g.group_code, g.status,
               s.school_key, subj.subject_name
        FROM msi_v2.groups g
        JOIN msi_v2.schools s ON s.id = g.school_id
        JOIN msi_v2.subject_programs sp ON sp.id = g.program_id
        JOIN msi_v2.subjects subj ON subj.id = sp.subject_id
        WHERE {_GROUP_MATCH}
        """,
        (int(group_id), int(group_id)),
    ).fetchone()


def count_group_dependencies(conn, group_id):
    counts = {}
    for key, table in (
        ("enrollments", "group_students"),
        ("schedules", "group_schedule_rules"),
        ("lessons", "lesson_sessions"),
        ("attendance", "attendance_records"),
        ("homework", "homework_scores"),
        ("exams", "exam_results"),
    ):
        row = conn.execute(
            f"SELECT count(*) AS total FROM msi_v2.{table} WHERE group_id = %s",
            (int(group_id),),
        ).fetchone()
        counts[key] = int(row["total"] or 0) if row else 0
    return counts


def archive_group(conn, group_id):
    return conn.execute(
        """UPDATE msi_v2.groups
           SET status = 'archived', updated_at = now()
           WHERE id = %s AND status <> 'archived'
           RETURNING id""",
        (int(group_id),),
    ).fetchone()


def purge_group(conn, group_id):
    return conn.execute(
        """DELETE FROM msi_v2.groups
           WHERE id = %s AND status = 'archived'
           RETURNING id""",
        (int(group_id),),
    ).fetchone()


def insert_audit_event(
    conn,
    *,
    event_type,
    entity_type,
    entity_id,
    detail_json,
    actor_staff_id=None,
    actor_account_id=None,
):
    conn.execute(
        """INSERT INTO msi_v2.audit_events (
             actor_staff_id, actor_account_id, event_type, entity_type,
             entity_id, detail_json, created_at
           ) VALUES (%s, %s, %s, %s, %s, %s::jsonb, now())""",
        (
            int(actor_staff_id) if actor_staff_id else None,
            int(actor_account_id) if actor_account_id else None,
            str(event_type),
            str(entity_type),
            int(entity_id),
            str(detail_json),
        ),
    )


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
    return conn.execute(
        """
        INSERT INTO msi_v2.groups (
          school_id, program_id, group_name, group_code, status, legacy_group_id,
          class_id, set_name
        ) VALUES (%s, %s, %s, %s, 'active', %s, %s, %s)
        RETURNING id
        """,
        (int(school_id), int(program_id), group_name, str(group_code or ""),
         int(legacy_group_id), int(class_id) if class_id else None, str(set_name or "Set 1")),
    ).fetchone()


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
