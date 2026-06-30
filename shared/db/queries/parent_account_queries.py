"""Parent CLIENT account queries against the clean msi_v2 schema.

Parents are Telegram/invite clients (no web password login). They live in
`msi_v2.parents` and link to students via `msi_v2.parent_student_links`. The
external ids exposed here are: parent_id = `msi_v2.parents.id`, student_row_id =
`msi_v2.students.legacy_student_row_id`, dashboard id =
`legacy_public_dashboard_id`.
"""


def _clean_username(value):
    return str(value or "").strip().lstrip("@").strip()


def _clean_positive_int(value):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


# Subjects derived from a student's active enrollments (st = msi_v2.students alias).
_STUDENT_SUBJECTS_SUBQUERY = """
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

# Student columns shared by the parent child-list queries.
_CHILD_STUDENT_COLUMNS = f"""
    st.legacy_student_row_id AS student_row_id,
    st.full_name AS student_full_name,
    st.student_code AS student_id,
    st.password_plain AS password,
    {_STUDENT_SUBJECTS_SUBQUERY} AS subjects,
    st.telegram_user_id AS student_telegram_user_id,
    st.photo_url,
    st.profile_description,
    st.class_name,
    COALESCE(sch.school_name, '') AS school_name,
    COALESCE(to_char(st.last_seen_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'), '') AS last_seen_at
"""

_PARENT_COLUMNS = """
    p.id AS parent_id,
    p.display_name AS full_name,
    p.phone,
    p.telegram_username,
    p.telegram_user_id,
    p.legacy_admin_id AS source_admin_id,
    to_char(p.created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS created_at,
    to_char(p.updated_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS updated_at
"""


def _parent_row(conn, parent_id):
    return conn.execute(
        """
        SELECT id, display_name AS full_name, phone, telegram_username,
               telegram_user_id, legacy_admin_id AS source_admin_id,
               created_at, updated_at
        FROM msi_v2.parents
        WHERE id = %s
        """,
        (int(parent_id),),
    ).fetchone()


def _resolve_student_v2_id(conn, student_row_id):
    row = conn.execute(
        "SELECT id FROM msi_v2.students WHERE legacy_student_row_id = %s",
        (int(student_row_id),),
    ).fetchone()
    return int(row["id"]) if row else None


def link_parent_from_invite(
    conn,
    *,
    student_row_id,
    full_name,
    phone,
    telegram_username,
    now,
    telegram_user_id=None,
):
    """Create or update a parent from an invite, then link to the student.

    Telegram Mini App claims are anchored by the verified ``telegram_user_id``.
    Manual fallbacks stay idempotent per student by matching username or phone.
    Returns the parent row.
    """
    student_v2_id = _resolve_student_v2_id(conn, student_row_id)
    if student_v2_id is None:
        return None

    full_name = str(full_name or "").strip()
    phone = str(phone or "").strip()
    username = _clean_username(telegram_username)
    telegram_user_id = _clean_positive_int(telegram_user_id)

    if telegram_user_id is not None:
        existing = conn.execute(
            """
            SELECT id FROM msi_v2.parents
            WHERE telegram_user_id = %s
            ORDER BY id ASC LIMIT 1
            """,
            (telegram_user_id,),
        ).fetchone()
    else:
        existing = conn.execute(
            """
            SELECT p.id
            FROM msi_v2.parents p
            JOIN msi_v2.parent_student_links l ON l.parent_id = p.id
            WHERE l.student_id = %s
              AND (
                  (%s <> '' AND lower(p.telegram_username) = lower(%s))
                  OR (%s <> '' AND p.phone = %s)
              )
            ORDER BY p.id ASC LIMIT 1
            """,
            (student_v2_id, username, username, phone, phone),
        ).fetchone()

    if existing:
        parent_id = int(existing["id"])
        conn.execute(
            """
            UPDATE msi_v2.parents
            SET display_name = CASE WHEN %s <> '' THEN %s ELSE display_name END,
                phone = CASE WHEN %s <> '' THEN %s ELSE phone END,
                telegram_username = CASE WHEN %s <> '' THEN %s ELSE telegram_username END,
                telegram_user_id = COALESCE(%s, telegram_user_id),
                updated_at = now()
            WHERE id = %s
            """,
            (full_name, full_name, phone, phone, username, username, telegram_user_id, parent_id),
        )
    else:
        inserted = conn.execute(
            """
            INSERT INTO msi_v2.parents (
                display_name, phone, telegram_username, telegram_user_id, status
            )
            VALUES (%s, %s, %s, %s, 'active')
            RETURNING id
            """,
            (full_name, phone, username, telegram_user_id),
        ).fetchone()
        parent_id = int(inserted["id"])

    conn.execute(
        """
        INSERT INTO msi_v2.parent_student_links (parent_id, student_id, relationship, status)
        VALUES (%s, %s, 'parent', 'active')
        ON CONFLICT (parent_id, student_id) DO UPDATE SET status = 'active'
        """,
        (parent_id, student_v2_id),
    )

    return _parent_row(conn, parent_id)


def get_parents_for_student(conn, student_row_id):
    """All linked parents for a student (admin visibility)."""
    return conn.execute(
        """
        SELECT p.id, p.display_name AS full_name, p.phone, p.telegram_username,
               p.telegram_user_id,
               to_char(l.created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS linked_at
        FROM msi_v2.parent_student_links l
        JOIN msi_v2.parents p ON p.id = l.parent_id
        JOIN msi_v2.students st ON st.id = l.student_id
        WHERE st.legacy_student_row_id = %s
        ORDER BY l.created_at ASC, p.id ASC
        """,
        (int(student_row_id),),
    ).fetchall()


def get_parent_by_telegram_id(conn, telegram_user_id):
    parsed = _clean_positive_int(telegram_user_id)
    if parsed is None:
        return None
    return conn.execute(
        """
        SELECT id, display_name AS full_name, phone, telegram_username,
               telegram_user_id, legacy_admin_id AS source_admin_id, created_at, updated_at
        FROM msi_v2.parents
        WHERE telegram_user_id = %s
        LIMIT 1
        """,
        (parsed,),
    ).fetchone()


def get_parent_child_link(conn, parent_id, student_row_id):
    parsed_parent_id = _clean_positive_int(parent_id)
    parsed_student_row_id = _clean_positive_int(student_row_id)
    if parsed_parent_id is None or parsed_student_row_id is None:
        return None
    return conn.execute(
        """
        SELECT l.parent_id, st.legacy_student_row_id AS student_row_id, l.created_at
        FROM msi_v2.parent_student_links l
        JOIN msi_v2.students st ON st.id = l.student_id
        WHERE l.parent_id = %s AND st.legacy_student_row_id = %s
        LIMIT 1
        """,
        (parsed_parent_id, parsed_student_row_id),
    ).fetchone()


def get_parent_child_link_by_dashboard_id(conn, parent_id, dashboard_student_id):
    parsed_parent_id = _clean_positive_int(parent_id)
    parsed_dashboard_student_id = _clean_positive_int(dashboard_student_id)
    if parsed_parent_id is None or parsed_dashboard_student_id is None:
        return None
    return conn.execute(
        """
        SELECT l.parent_id, st.legacy_student_row_id AS student_row_id,
               COALESCE(gs.legacy_public_dashboard_id, st.legacy_public_dashboard_id) AS public_dashboard_id
        FROM msi_v2.parent_student_links l
        JOIN msi_v2.students st ON st.id = l.student_id
        JOIN msi_v2.group_students gs ON gs.student_id = st.id
        WHERE l.parent_id = %s
          AND COALESCE(gs.legacy_public_dashboard_id, st.legacy_public_dashboard_id) = %s
          AND gs.enrollment_status = 'active'
        LIMIT 1
        """,
        (parsed_parent_id, parsed_dashboard_student_id),
    ).fetchone()


def clear_parent_telegram_user_conflicts(conn, telegram_user_id, parent_id=None):
    parsed_telegram_user_id = _clean_positive_int(telegram_user_id)
    if parsed_telegram_user_id is None:
        return
    if parent_id is not None:
        parsed_parent_id = _clean_positive_int(parent_id)
        if parsed_parent_id is None:
            return
        conn.execute(
            """
            UPDATE msi_v2.parents
            SET telegram_user_id = NULL
            WHERE telegram_user_id = %s AND id <> %s
            """,
            (parsed_telegram_user_id, parsed_parent_id),
        )
        return
    conn.execute(
        "UPDATE msi_v2.parents SET telegram_user_id = NULL WHERE telegram_user_id = %s",
        (parsed_telegram_user_id,),
    )


def list_parent_client_child_rows(conn, parent_id):
    return conn.execute(
        f"""
        SELECT
            {_PARENT_COLUMNS},
            to_char(l.created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS linked_at,
            {_CHILD_STUDENT_COLUMNS}
        FROM msi_v2.parent_student_links l
        JOIN msi_v2.parents p ON p.id = l.parent_id
        JOIN msi_v2.students st ON st.id = l.student_id
        LEFT JOIN msi_v2.schools sch ON sch.id = st.school_id
        WHERE p.id = %s
        ORDER BY lower(st.full_name) ASC, st.id ASC
        """,
        (int(parent_id),),
    ).fetchall()


def list_invite_parent_rows(conn):
    """All parent CLIENT accounts with their linked students, for admin visibility."""
    return conn.execute(
        f"""
        SELECT
            {_PARENT_COLUMNS},
            to_char(l.created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS linked_at,
            {_CHILD_STUDENT_COLUMNS}
        FROM msi_v2.parents p
        LEFT JOIN msi_v2.parent_student_links l ON l.parent_id = p.id
        LEFT JOIN msi_v2.students st ON st.id = l.student_id
        LEFT JOIN msi_v2.schools sch ON sch.id = st.school_id
        ORDER BY lower(p.display_name) ASC, p.id ASC, lower(st.full_name) ASC, st.id ASC
        """
    ).fetchall()


__all__ = [
    "clear_parent_telegram_user_conflicts",
    "get_parent_by_telegram_id",
    "get_parent_child_link",
    "get_parent_child_link_by_dashboard_id",
    "get_parents_for_student",
    "link_parent_from_invite",
    "list_invite_parent_rows",
    "list_parent_client_child_rows",
]
