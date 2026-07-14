"""Student SQL helpers against the current LMS schema.

The external "student_row_id" used by sessions, the admin UI and the bot is the
``msi_v2.students.legacy_student_row_id`` value (the migrated id for existing
students, a freshly minted high-band id for students created after the cutover).
Every lookup here resolves a student by that legacy id and uses the msi_v2
primary key only for internal joins.

DB-3 owns student query access here while the physical schema remains
``msi_v2``. This module is the canonical owner of student SQL.
"""

_DEFAULT_SCHOOL_KEY = "school5"


def _normalize_school_key(school_key):
    normalized = str(school_key or "").strip().casefold()
    if normalized in {"school_5", "school-5", "school 5", "school5"}:
        return "school5"
    if normalized in {"sehriyo", "sehriyo school"}:
        return "sehriyo"
    return normalized or _DEFAULT_SCHOOL_KEY


# Reusable scalar subqueries (st = msi_v2.students alias in the outer query).
_SUBJECTS_SUBQUERY = """
    COALESCE((
        SELECT string_agg(s.subject_name, ', ' ORDER BY s.subject_name)
        FROM (
            SELECT DISTINCT subj.subject_name
            FROM msi_v2.group_students gs
            JOIN msi_v2.groups g ON g.id = gs.group_id
            JOIN msi_v2.subject_programs sp ON sp.id = g.program_id
            JOIN msi_v2.subjects subj ON subj.id = sp.subject_id
            WHERE gs.student_id = st.id AND gs.enrollment_status = 'active'
        ) s
    ), '')
"""

_ENROLLMENT_ID_SUBQUERY = """
    COALESCE(
        (
            SELECT min(gs.legacy_public_dashboard_id)
            FROM msi_v2.group_students gs
            WHERE gs.student_id = st.id AND gs.legacy_public_dashboard_id IS NOT NULL
        ),
        st.legacy_public_dashboard_id
    )
"""


def get_next_student_code(conn, prefix="MSI"):
    normalized_prefix = str(prefix or "MSI").strip().upper() or "MSI"
    rows = conn.execute(
        "SELECT student_code FROM msi_v2.students WHERE upper(student_code) LIKE %s",
        (f"{normalized_prefix}%",),
    ).fetchall()
    max_num = 0
    prefix_length = len(normalized_prefix)
    for row in rows:
        raw = str(row["student_code"] or "").strip().upper()
        if not raw.startswith(normalized_prefix):
            continue
        numeric_part = raw[prefix_length:]
        if numeric_part.isdigit():
            max_num = max(max_num, int(numeric_part))
    return f"{normalized_prefix}{max_num + 1:05d}"


def get_student_enrollment_map_row(conn, enrollment_id, school_key=_DEFAULT_SCHOOL_KEY):
    """Resolve a student (legacy id) from a public dashboard id.

    Dashboard ids are globally unique in msi_v2, so the school key is accepted
    for signature compatibility but not used to scope the lookup.
    """
    return conn.execute(
        """
        SELECT st.id AS student_db_id,
               st.legacy_student_row_id AS student_row_id
        FROM msi_v2.group_students gs
        JOIN msi_v2.students st ON st.id = gs.student_id
        WHERE COALESCE(gs.legacy_public_dashboard_id, st.legacy_public_dashboard_id) = %s
          AND st.legacy_student_row_id IS NOT NULL
        LIMIT 1
        """,
        (enrollment_id,),
    ).fetchone()


def get_student_ref_by_public_dashboard_id(conn, public_dashboard_id):
    return conn.execute(
        """
        SELECT st.id AS student_id, st.school_id
        FROM msi_v2.group_students gs
        JOIN msi_v2.students st ON st.id = gs.student_id
        WHERE COALESCE(gs.legacy_public_dashboard_id, st.legacy_public_dashboard_id) = %s
        LIMIT 1
        """,
        (public_dashboard_id,),
    ).fetchone()


def get_student_ref_by_public_dashboard_id_and_school(conn, public_dashboard_id, school_code=""):
    return conn.execute(
        """
        SELECT
            st.id AS internal_student_id,
            st.legacy_student_row_id,
            st.full_name,
            sch.school_key
        FROM msi_v2.students st
        LEFT JOIN msi_v2.schools sch ON sch.id = st.school_id
        LEFT JOIN msi_v2.group_students gs ON gs.student_id = st.id
        WHERE COALESCE(gs.legacy_public_dashboard_id, st.legacy_public_dashboard_id) = %s
          AND (%s = '' OR lower(sch.school_key) = lower(%s))
        LIMIT 1
        """,
        (public_dashboard_id, str(school_code or "").strip(), str(school_code or "").strip()),
    ).fetchone()


def list_subject_enrollment_rows_for_student(conn, student_id, school_id):
    return conn.execute(
        """
        SELECT COALESCE(gs.legacy_public_dashboard_id, st.legacy_public_dashboard_id) AS id,
               sub.subject_name AS subject,
               g.group_name AS grp
        FROM msi_v2.group_students gs
        JOIN msi_v2.students st ON st.id = gs.student_id
        JOIN msi_v2.groups g ON g.id = gs.group_id
        JOIN msi_v2.subject_programs sp ON sp.id = g.program_id
        JOIN msi_v2.subjects sub ON sub.id = sp.subject_id
        WHERE gs.enrollment_status = 'active'
          AND st.id = %s
          AND st.school_id = %s
          AND COALESCE(gs.legacy_public_dashboard_id, st.legacy_public_dashboard_id) IS NOT NULL
        ORDER BY sub.subject_name, g.group_name
        """,
        (student_id, school_id),
    ).fetchall()


def list_active_subject_options_for_student(conn, student_id):
    return conn.execute(
        """
        SELECT DISTINCT subj.id, subj.subject_name AS name
        FROM msi_v2.group_students gs
        JOIN msi_v2.groups g ON g.id = gs.group_id
        JOIN msi_v2.subject_programs sp ON sp.id = g.program_id
        JOIN msi_v2.subjects subj ON subj.id = sp.subject_id
        WHERE gs.student_id = %s
          AND gs.enrollment_status = 'active'
          AND subj.status = 'active'
        ORDER BY subj.subject_name
        """,
        (student_id,),
    ).fetchall()


def update_student_last_seen(conn, student_db_id, now):
    updated = conn.execute(
        """
        UPDATE msi_v2.students
        SET last_seen_at = %s::timestamptz
        WHERE id = %s
        """,
        (now, student_db_id),
    )
    return int(updated.rowcount or 0)


def list_students_for_admin_rows(conn, school_key="", school_name=""):
    normalized_school_key = str(school_key or "").strip().casefold()
    base = f"""
        SELECT
            st.legacy_student_row_id AS id,
            st.full_name,
            st.student_code AS student_id,
            {_SUBJECTS_SUBQUERY} AS subjects,
            st.telegram_user_id,
            st.photo_url,
            st.profile_description,
            st.class_name,
            COALESCE(sch.school_name, '') AS school_name,
            COALESCE(to_char(st.last_seen_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'), '') AS last_seen_at
        FROM msi_v2.students st
        LEFT JOIN msi_v2.schools sch ON sch.id = st.school_id
        WHERE st.legacy_student_row_id IS NOT NULL
    """
    if normalized_school_key:
        return conn.execute(
            base + " AND lower(sch.school_key) = lower(%s) ORDER BY st.legacy_student_row_id ASC",
            (_normalize_school_key(normalized_school_key),),
        ).fetchall()
    normalized_school_name = str(school_name or "").strip()
    if normalized_school_name:
        return conn.execute(
            base + " AND lower(sch.school_name) = lower(%s) ORDER BY st.legacy_student_row_id ASC",
            (normalized_school_name,),
        ).fetchall()
    return conn.execute(base + " ORDER BY st.legacy_student_row_id ASC").fetchall()


def list_online_only_student_rows(conn):
    return conn.execute(
        """
        SELECT DISTINCT st.full_name, s.school_name AS school_name
        FROM msi_v2.group_students gs
        JOIN msi_v2.students st ON st.id = gs.student_id
        JOIN msi_v2.groups g ON g.id = gs.group_id
        JOIN msi_v2.schools s ON s.id = g.school_id
        WHERE gs.enrollment_status = 'active'
          AND lower(g.group_name) = 'online'
          AND NOT EXISTS (
            SELECT 1
            FROM msi_v2.group_students other_gs
            JOIN msi_v2.groups other_g ON other_g.id = other_gs.group_id
            JOIN msi_v2.students other_st ON other_st.id = other_gs.student_id
            WHERE other_g.school_id = g.school_id
              AND lower(trim(other_st.full_name)) = lower(trim(st.full_name))
              AND other_gs.enrollment_status = 'active'
              AND lower(other_g.group_name) <> 'online'
          )
        """
    ).fetchall()


def get_student_admin_row(conn, student_row_id):
    return conn.execute(
        f"""
        SELECT
            st.legacy_student_row_id AS id,
            st.full_name,
            st.student_code AS student_id,
            {_SUBJECTS_SUBQUERY} AS subjects,
            st.photo_url,
            st.profile_description,
            st.class_name,
            COALESCE(sch.school_name, '') AS school_name,
            st.teacher_name
        FROM msi_v2.students st
        LEFT JOIN msi_v2.schools sch ON sch.id = st.school_id
        WHERE st.legacy_student_row_id = %s
        """,
        (student_row_id,),
    ).fetchone()


def get_student_admin_row_by_id(conn, student_db_id):
    return conn.execute(
        f"""
        SELECT
            st.id AS student_db_id,
            st.legacy_student_row_id AS id,
            st.full_name,
            st.student_code AS student_id,
            {_SUBJECTS_SUBQUERY} AS subjects,
            st.photo_url,
            st.profile_description,
            st.class_name,
            COALESCE(sch.school_name, '') AS school_name,
            st.teacher_name
        FROM msi_v2.students st
        LEFT JOIN msi_v2.schools sch ON sch.id = st.school_id
        WHERE st.id = %s
        """,
        (int(student_db_id),),
    ).fetchone()


def get_active_enrollment_for_student_row(conn, student_row_id):
    return conn.execute(
        """
        SELECT gs.group_id, gs.student_id, g.group_name
        FROM msi_v2.group_students gs
        JOIN msi_v2.students st ON st.id = gs.student_id
        JOIN msi_v2.groups g ON g.id = gs.group_id
        WHERE st.legacy_student_row_id = %s AND gs.enrollment_status = 'active'
        LIMIT 1
        """,
        (student_row_id,),
    ).fetchone()


def list_active_student_enrollments(conn):
    return conn.execute(
        """
        SELECT gs.group_id, gs.student_id, g.group_name, st.full_name
        FROM msi_v2.group_students gs
        JOIN msi_v2.students st ON st.id = gs.student_id
        JOIN msi_v2.groups g ON g.id = gs.group_id
        WHERE gs.enrollment_status = 'active'
        """
    ).fetchall()


def list_classmate_names(conn, group_id, student_id):
    return conn.execute(
        """
        SELECT st.full_name
        FROM msi_v2.group_students gs
        JOIN msi_v2.students st ON st.id = gs.student_id
        WHERE gs.group_id = %s AND gs.enrollment_status = 'active'
          AND gs.student_id != %s
        ORDER BY st.full_name
        """,
        (int(group_id), int(student_id)),
    ).fetchall()


def list_public_dashboard_targets_for_student_row(conn, student_row_id):
    return conn.execute(
        """
        SELECT
            COALESCE(gs.legacy_public_dashboard_id, st.legacy_public_dashboard_id) AS public_dashboard_id,
            sub.subject_name,
            g.group_name,
            s.school_key
        FROM msi_v2.students st
        JOIN msi_v2.group_students gs ON gs.student_id = st.id
        JOIN msi_v2.groups g ON g.id = gs.group_id
        JOIN msi_v2.schools s ON s.id = g.school_id
        JOIN msi_v2.subject_programs sp ON sp.id = g.program_id
        JOIN msi_v2.subjects sub ON sub.id = sp.subject_id
        WHERE st.legacy_student_row_id = %s
          AND gs.enrollment_status = 'active'
          AND COALESCE(gs.legacy_public_dashboard_id, st.legacy_public_dashboard_id) IS NOT NULL
        ORDER BY g.group_name, sub.subject_name
        """,
        (student_row_id,),
    ).fetchall()


def update_student_admin_profile(
    conn,
    student_row_id,
    photo_url,
    profile_description,
    class_name,
    school_name,
    teacher_name,
):
    conn.execute(
        """
        UPDATE msi_v2.students
        SET
            photo_url = %s,
            profile_description = %s,
            class_name = %s,
            teacher_name = %s,
            school_id = COALESCE(
                (
                    SELECT id FROM msi_v2.schools
                    WHERE lower(school_name) = lower(%s) OR lower(school_key) = lower(%s)
                    LIMIT 1
                ),
                school_id
            )
        WHERE legacy_student_row_id = %s
        """,
        (
            photo_url,
            profile_description,
            class_name,
            teacher_name,
            school_name,
            school_name,
            student_row_id,
        ),
    )


def get_student_conflict_by_telegram_id(conn, telegram_user_id, student_row_id):
    return conn.execute(
        """
        SELECT st.legacy_student_row_id AS id
        FROM msi_v2.students st
        WHERE st.telegram_user_id = %s
          AND COALESCE(st.legacy_student_row_id, -999) != %s
        """,
        (telegram_user_id, student_row_id),
    ).fetchone()


def clear_student_telegram_user_conflicts(conn, telegram_user_id, student_row_id):
    conn.execute(
        """
        UPDATE msi_v2.students
        SET telegram_user_id = NULL
        WHERE telegram_user_id = %s
          AND COALESCE(legacy_student_row_id, -999) != %s
        """,
        (telegram_user_id, student_row_id),
    )


def update_student_telegram_user(conn, telegram_user_id, student_row_id):
    conn.execute(
        "UPDATE msi_v2.students SET telegram_user_id = %s WHERE legacy_student_row_id = %s",
        (telegram_user_id, student_row_id),
    )


def get_student_by_telegram_id(conn, telegram_user_id):
    return conn.execute(
        f"""
        SELECT
            st.legacy_student_row_id AS id,
            st.full_name,
            st.student_code AS student_id,
            {_SUBJECTS_SUBQUERY} AS subjects,
            sch.school_key,
            {_ENROLLMENT_ID_SUBQUERY} AS enrollment_id
        FROM msi_v2.students st
        LEFT JOIN msi_v2.schools sch ON sch.id = st.school_id
        WHERE st.telegram_user_id = %s
        """,
        (telegram_user_id,),
    ).fetchone()


__all__ = [
    "get_next_student_code",
    "get_student_enrollment_map_row",
    "get_student_ref_by_public_dashboard_id",
    "get_student_ref_by_public_dashboard_id_and_school",
    "list_subject_enrollment_rows_for_student",
    "list_active_subject_options_for_student",
    "update_student_last_seen",
    "list_students_for_admin_rows",
    "list_online_only_student_rows",
    "get_student_admin_row",
    "get_student_admin_row_by_id",
    "get_active_enrollment_for_student_row",
    "list_active_student_enrollments",
    "list_classmate_names",
    "list_public_dashboard_targets_for_student_row",
    "update_student_admin_profile",
    "get_student_conflict_by_telegram_id",
    "clear_student_telegram_user_conflicts",
    "update_student_telegram_user",
    "get_student_by_telegram_id",
]
