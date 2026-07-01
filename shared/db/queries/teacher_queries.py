"""Teacher SQL helpers backed by msi_v2."""


def _teacher_select():
    return """
        t.id,
        t.full_name,
        0::float AS pay_rate,
        COALESCE(g.group_name, '') AS assigned_group,
        'teacher' AS category,
        '' AS semester_stage,
        7::float AS performance_score,
        0::integer AS supervised_lessons,
        '' AS igcse_evidence,
        t.notes AS promotion_notes,
        t.created_at::text AS created_at,
        t.updated_at::text AS updated_at,
        staff.login AS login,
        '' AS password
    """


def list_teachers_rows(conn):
    return conn.execute(
        f"""
        SELECT {_teacher_select()}
        FROM msi_v2.teachers t
        LEFT JOIN msi_v2.group_teachers gt ON gt.teacher_id = t.id AND gt.status = 'active'
        LEFT JOIN msi_v2.groups g ON g.id = gt.group_id
        LEFT JOIN msi_v2.msi_staff staff
            ON staff.telegram_user_id = t.telegram_user_id
            OR lower(staff.display_name) = lower(t.full_name)
        ORDER BY lower(t.full_name) ASC, t.id ASC
        """
    ).fetchall()


def get_teacher_login_row(conn, login):
    return conn.execute(
        """
        SELECT
            staff.id,
            COALESCE(NULLIF(staff.display_name, ''), staff.login) AS full_name,
            '' AS assigned_group,
            staff.login,
            staff.password_hash
        FROM msi_v2.msi_staff staff
        WHERE lower(staff.login) = lower(%s)
          AND lower(staff.role) = 'teacher'
        LIMIT 1
        """,
        (login,),
    ).fetchone()


def get_teacher_auth_row_by_id(conn, teacher_id):
    return conn.execute(
        """
        SELECT
            t.id AS teacher_id,
            COALESCE(staff.login, '') AS login,
            '' AS password,
            COALESCE(staff.password_hash, '') AS password_hash
        FROM msi_v2.teachers t
        LEFT JOIN msi_v2.msi_staff staff
            ON staff.telegram_user_id = t.telegram_user_id
            OR lower(staff.display_name) = lower(t.full_name)
        WHERE t.id = %s
        LIMIT 1
        """,
        (teacher_id,),
    ).fetchone()


def list_teacher_ids_without_auth(conn):
    return conn.execute(
        """
        SELECT t.id
        FROM msi_v2.teachers t
        LEFT JOIN msi_v2.msi_staff staff
            ON staff.telegram_user_id = t.telegram_user_id
            OR lower(staff.display_name) = lower(t.full_name)
        WHERE staff.id IS NULL
        ORDER BY t.id ASC
        """
    ).fetchall()


def get_next_teacher_code(conn, prefix="TCH"):
    normalized_prefix = str(prefix or "TCH").strip().upper() or "TCH"
    row = conn.execute(
        """
        SELECT COALESCE(MAX(NULLIF(regexp_replace(upper(login), %s, ''), '')::integer), 0) AS max_num
        FROM msi_v2.msi_staff
        WHERE upper(login) ~ %s
        """,
        (f"^{normalized_prefix}", f"^{normalized_prefix}[0-9]+$"),
    ).fetchone()
    return f"{normalized_prefix}{int(row['max_num'] or 0) + 1:03d}"


def insert_teacher_auth(conn, teacher_id, login, password, password_hash, updated_at):
    teacher = get_teacher_by_id_row(conn, teacher_id)
    display_name = str(teacher["full_name"] if teacher else "").strip() or str(login)
    conn.execute(
        """
        INSERT INTO msi_v2.msi_staff (
            login, password_hash, display_name, role, status, created_at, updated_at
        )
        VALUES (%s, %s, %s, 'teacher', 'active', now(), COALESCE(NULLIF(%s, '')::timestamptz, now()))
        ON CONFLICT DO NOTHING
        """,
        (login, password_hash, display_name, updated_at),
    )


def update_teacher_password(conn, teacher_id, plain_password, password_hash, updated_at):
    auth = get_teacher_auth_row_by_id(conn, teacher_id)
    login = str(auth["login"] if auth else "").strip()
    if not login:
        return
    conn.execute(
        """
        UPDATE msi_v2.msi_staff
        SET password_hash = %s, updated_at = COALESCE(NULLIF(%s, '')::timestamptz, now())
        WHERE lower(login) = lower(%s)
        """,
        (password_hash, updated_at, login),
    )


def get_teacher_by_id_row(conn, teacher_id):
    return conn.execute(
        f"""
        SELECT {_teacher_select()}
        FROM msi_v2.teachers t
        LEFT JOIN msi_v2.group_teachers gt ON gt.teacher_id = t.id AND gt.status = 'active'
        LEFT JOIN msi_v2.groups g ON g.id = gt.group_id
        LEFT JOIN msi_v2.msi_staff staff
            ON staff.telegram_user_id = t.telegram_user_id
            OR lower(staff.display_name) = lower(t.full_name)
        WHERE t.id = %s
        LIMIT 1
        """,
        (teacher_id,),
    ).fetchone()


def insert_teacher_row(
    conn,
    full_name,
    pay_rate,
    assigned_group,
    category,
    semester_stage,
    performance_score,
    supervised_lessons,
    igcse_evidence,
    promotion_notes,
    created_at,
    updated_at,
):
    conn.execute(
        """
        INSERT INTO msi_v2.teachers (full_name, notes, status, created_at, updated_at)
        VALUES (%s, %s, 'active', COALESCE(NULLIF(%s, '')::timestamptz, now()), COALESCE(NULLIF(%s, '')::timestamptz, now()))
        ON CONFLICT DO NOTHING
        """,
        (full_name, promotion_notes or "", created_at, updated_at),
    )


def get_teacher_by_group_row(conn, group_name):
    return conn.execute(
        f"""
        SELECT {_teacher_select()}
        FROM msi_v2.teachers t
        JOIN msi_v2.group_teachers gt ON gt.teacher_id = t.id AND gt.status = 'active'
        JOIN msi_v2.groups g ON g.id = gt.group_id
        LEFT JOIN msi_v2.msi_staff staff
            ON staff.telegram_user_id = t.telegram_user_id
            OR lower(staff.display_name) = lower(t.full_name)
        WHERE lower(g.group_name) = lower(%s)
        ORDER BY t.id ASC
        LIMIT 1
        """,
        (group_name,),
    ).fetchone()


def get_teacher_by_full_name_row(conn, full_name):
    return conn.execute(
        f"""
        SELECT {_teacher_select()}
        FROM msi_v2.teachers t
        LEFT JOIN msi_v2.group_teachers gt ON gt.teacher_id = t.id AND gt.status = 'active'
        LEFT JOIN msi_v2.groups g ON g.id = gt.group_id
        LEFT JOIN msi_v2.msi_staff staff
            ON staff.telegram_user_id = t.telegram_user_id
            OR lower(staff.display_name) = lower(t.full_name)
        WHERE lower(t.full_name) = lower(%s)
        ORDER BY t.id ASC
        LIMIT 1
        """,
        (full_name,),
    ).fetchone()


def delete_teacher_by_group(conn, group_name):
    conn.execute(
        """
        UPDATE msi_v2.group_teachers gt
        SET status = 'inactive'
        FROM msi_v2.groups g
        WHERE g.id = gt.group_id AND lower(g.group_name) = lower(%s)
        """,
        (group_name,),
    )


def update_teacher_row_by_id(
    conn,
    teacher_id,
    full_name,
    pay_rate,
    assigned_group,
    category,
    semester_stage,
    performance_score,
    supervised_lessons,
    igcse_evidence,
    promotion_notes,
    updated_at,
):
    conn.execute(
        """
        UPDATE msi_v2.teachers
        SET full_name = %s,
            notes = %s,
            updated_at = COALESCE(NULLIF(%s, '')::timestamptz, now())
        WHERE id = %s
        """,
        (full_name, promotion_notes or "", updated_at, teacher_id),
    )


def delete_teacher_row_by_id(conn, teacher_id):
    conn.execute(
        """
        UPDATE msi_v2.teachers
        SET status = 'inactive', updated_at = now()
        WHERE id = %s
        """,
        (teacher_id,),
    )


__all__ = [
    "list_teachers_rows",
    "get_teacher_login_row",
    "get_teacher_auth_row_by_id",
    "list_teacher_ids_without_auth",
    "get_next_teacher_code",
    "insert_teacher_auth",
    "update_teacher_password",
    "get_teacher_by_id_row",
    "insert_teacher_row",
    "get_teacher_by_group_row",
    "get_teacher_by_full_name_row",
    "delete_teacher_by_group",
    "update_teacher_row_by_id",
    "delete_teacher_row_by_id",
]
