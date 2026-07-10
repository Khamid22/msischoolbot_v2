"""Teacher persistence owned by the teacher module.

The physical PostgreSQL schema remains ``msi_v2``. HTTP adapters and other
modules must call the teacher service instead of importing this repository.
"""

import re


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
        COALESCE(account.login, staff.login, '') AS login
    """


def list_teachers_rows(conn):
    # DISTINCT ON (t.id) collapses the group_teachers/staff joins to one row per
    # teacher (a teacher can have several groups); the outer query keeps the
    # name ordering the admin panel expects.
    return conn.execute(
        f"""
        SELECT * FROM (
            SELECT DISTINCT ON (t.id) {_teacher_select()}
            FROM msi_v2.teachers t
            LEFT JOIN msi_v2.group_teachers gt ON gt.teacher_id = t.id AND gt.status = 'active'
            LEFT JOIN msi_v2.groups g ON g.id = gt.group_id
            LEFT JOIN msi_v2.msi_staff staff ON staff.teacher_id = t.id
            LEFT JOIN msi_v2.teacher_profiles profile ON profile.teacher_id = t.id
            LEFT JOIN msi_v2.accounts account ON account.id = profile.account_id
            WHERE t.status = 'active'
            ORDER BY t.id, g.group_name NULLS LAST
        ) teacher_rows
        ORDER BY lower(teacher_rows.full_name) ASC, teacher_rows.id ASC
        """
    ).fetchall()


def get_teacher_login_row(conn, login):
    return conn.execute(
        """
        SELECT
            COALESCE(staff.teacher_id, name_match.id, 0) AS id,
            staff.id AS staff_id,
            COALESCE(NULLIF(t.full_name, ''), NULLIF(name_match.full_name, ''), NULLIF(staff.display_name, ''), staff.login) AS full_name,
            COALESCE(g.group_name, '') AS assigned_group,
            staff.login,
            staff.password_hash
        FROM msi_v2.msi_staff staff
        LEFT JOIN msi_v2.teachers t ON t.id = staff.teacher_id
        LEFT JOIN msi_v2.teachers name_match
          ON staff.teacher_id IS NULL
         AND lower(name_match.full_name) = lower(COALESCE(NULLIF(staff.display_name, ''), staff.login))
         AND name_match.status <> 'inactive'
        LEFT JOIN msi_v2.group_teachers gt
          ON gt.teacher_id = COALESCE(t.id, name_match.id)
         AND gt.status = 'active'
         AND gt.role = 'main'
        LEFT JOIN msi_v2.groups g ON g.id = gt.group_id
        WHERE lower(staff.login) = lower(%s)
          AND lower(staff.role) = 'teacher'
          AND lower(staff.status) = 'active'
        LIMIT 1
        """,
        (login,),
    ).fetchone()


def get_teacher_by_telegram_id(conn, telegram_user_id):
    return conn.execute(
        """
        SELECT
            COALESCE(staff.teacher_id, name_match.id, 0) AS id,
            staff.id AS staff_id,
            COALESCE(NULLIF(t.full_name, ''), NULLIF(name_match.full_name, ''), NULLIF(staff.display_name, ''), staff.login) AS full_name,
            COALESCE(g.group_name, '') AS assigned_group,
            staff.login,
            staff.password_hash
        FROM msi_v2.msi_staff staff
        LEFT JOIN msi_v2.teachers t ON t.id = staff.teacher_id
        LEFT JOIN msi_v2.teachers name_match
          ON staff.teacher_id IS NULL
         AND lower(name_match.full_name) = lower(COALESCE(NULLIF(staff.display_name, ''), staff.login))
         AND name_match.status <> 'inactive'
        LEFT JOIN msi_v2.group_teachers gt
          ON gt.teacher_id = COALESCE(t.id, name_match.id)
         AND gt.status = 'active'
         AND gt.role = 'main'
        LEFT JOIN msi_v2.groups g ON g.id = gt.group_id
        WHERE staff.telegram_user_id = %s
          AND lower(staff.role) = 'teacher'
          AND lower(staff.status) = 'active'
        LIMIT 1
        """,
        (telegram_user_id,),
    ).fetchone()


def get_teacher_auth_row_by_id(conn, teacher_id):
    return conn.execute(
        """
        SELECT
            t.id AS teacher_id,
            COALESCE(account.login, staff.login, '') AS login,
            COALESCE(account.password_hash, staff.password_hash, '') AS password_hash,
            staff.id AS staff_id
        FROM msi_v2.teachers t
        LEFT JOIN msi_v2.msi_staff staff ON staff.teacher_id = t.id
        LEFT JOIN msi_v2.teacher_profiles profile ON profile.teacher_id = t.id
        LEFT JOIN msi_v2.accounts account ON account.id = profile.account_id
        WHERE t.id = %s
        LIMIT 1
        """,
        (teacher_id,),
    ).fetchone()


def list_teacher_ids_without_auth(conn):
    return conn.execute(
        """
        SELECT DISTINCT ON (t.id)
            t.id,
            t.full_name,
            COALESCE(group_subject.subject_name, direct_subject.subject_name, '') AS subject_name,
            COALESCE(g.group_name, '') AS assigned_group
        FROM msi_v2.teachers t
        LEFT JOIN msi_v2.group_teachers gt
          ON gt.teacher_id = t.id
         AND gt.status = 'active'
         AND gt.role = 'main'
        LEFT JOIN msi_v2.groups g ON g.id = gt.group_id
        LEFT JOIN msi_v2.subject_programs sp ON sp.id = g.program_id
        LEFT JOIN msi_v2.subjects group_subject ON group_subject.id = sp.subject_id
        LEFT JOIN msi_v2.teacher_subjects ts
          ON ts.teacher_id = t.id
         AND ts.status = 'active'
        LEFT JOIN msi_v2.subjects direct_subject ON direct_subject.id = ts.subject_id
        LEFT JOIN msi_v2.msi_staff staff ON staff.teacher_id = t.id
        LEFT JOIN msi_v2.teacher_profiles profile ON profile.teacher_id = t.id
        LEFT JOIN msi_v2.accounts account ON account.id = profile.account_id
        WHERE staff.id IS NULL
          AND t.status = 'active'
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
    return f"{normalized_prefix}{int(row['max_num'] or 0) + 1:04d}"


def get_next_teacher_login(conn, subject_prefix="tch"):
    normalized_prefix = re.sub(r"[^a-z0-9]+", "", str(subject_prefix or "").strip().lower()) or "tch"
    login_prefix = f"{normalized_prefix}t"
    rows = conn.execute(
        """
        SELECT lower(login) AS login
        FROM msi_v2.msi_staff
        WHERE lower(login) LIKE %s
        """,
        (f"{login_prefix}%",),
    ).fetchall()
    pattern = re.compile(rf"^{re.escape(login_prefix)}(\d+)$")
    max_num = 0
    for row in rows:
        match = pattern.match(str(row["login"] or ""))
        if match:
            max_num = max(max_num, int(match.group(1)))
    return f"{login_prefix}{max_num + 1:03d}"


def insert_teacher_auth(conn, teacher_id, login, password, password_hash, updated_at):
    teacher = get_teacher_by_id_row(conn, teacher_id)
    display_name = str(teacher["full_name"] if teacher else "").strip() or str(login)
    row = conn.execute(
        """
        INSERT INTO msi_v2.msi_staff (
            login, password_hash, display_name, role, status, teacher_id, created_at, updated_at
        )
        VALUES (%s, %s, %s, 'teacher', 'active', %s, now(), COALESCE(NULLIF(%s, '')::timestamptz, now()))
        ON CONFLICT ((lower(login))) DO UPDATE SET
            display_name = excluded.display_name,
            status = 'active',
            teacher_id = COALESCE(msi_staff.teacher_id, excluded.teacher_id),
            updated_at = excluded.updated_at
        WHERE lower(msi_staff.role) = 'teacher'
          AND (msi_staff.teacher_id IS NULL OR msi_staff.teacher_id = excluded.teacher_id)
        RETURNING id
        """,
        (login, password_hash, display_name, int(teacher_id), updated_at),
    ).fetchone()
    return int(row["id"]) if row else 0


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
        LEFT JOIN msi_v2.msi_staff staff ON staff.teacher_id = t.id
        LEFT JOIN msi_v2.teacher_profiles profile ON profile.teacher_id = t.id
        LEFT JOIN msi_v2.accounts account ON account.id = profile.account_id
        WHERE t.id = %s
        LIMIT 1
        """,
        (teacher_id,),
    ).fetchone()


def list_active_group_ids_by_name(conn, group_name):
    return conn.execute(
        """
        SELECT id FROM msi_v2.groups
        WHERE lower(group_name) = lower(%s) AND status = 'active'
        ORDER BY id
        """,
        (group_name,),
    ).fetchall()


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
    row = conn.execute(
        """
        INSERT INTO msi_v2.teachers (full_name, notes, status, created_at, updated_at)
        VALUES (%s, %s, 'active', COALESCE(NULLIF(%s, '')::timestamptz, now()), COALESCE(NULLIF(%s, '')::timestamptz, now()))
        RETURNING id
        """,
        (full_name, promotion_notes or "", created_at, updated_at),
    ).fetchone()
    teacher_id = int(row["id"]) if row else 0
    if teacher_id and str(assigned_group or "").strip():
        set_teacher_group_assignment(conn, teacher_id, assigned_group)
    return teacher_id


def insert_teacher_profile_row(conn, full_name, notes="", status="academy", subject_id=0, created_at="", updated_at=""):
    row = conn.execute(
        """
        INSERT INTO msi_v2.teachers (full_name, notes, status, created_at, updated_at)
        VALUES (
            %s, %s, %s,
            COALESCE(NULLIF(%s, '')::timestamptz, now()),
            COALESCE(NULLIF(%s, '')::timestamptz, now())
        )
        RETURNING id
        """,
        (
            str(full_name or "").strip(),
            str(notes or "").strip(),
            str(status or "academy").strip().lower() or "academy",
            created_at,
            updated_at,
        ),
    ).fetchone()
    teacher_id = int(row["id"]) if row else 0
    if teacher_id and int(subject_id or 0) > 0:
        upsert_teacher_subject(conn, teacher_id, int(subject_id))
    return teacher_id


def upsert_teacher_subject(conn, teacher_id, subject_id):
    conn.execute(
        """
        INSERT INTO msi_v2.teacher_subjects (teacher_id, subject_id, status, created_at)
        VALUES (%s, %s, 'active', now())
        ON CONFLICT (teacher_id, subject_id) DO UPDATE SET status = 'active'
        """,
        (int(teacher_id), int(subject_id)),
    )


def set_teacher_group_assignment(conn, teacher_id, group_name):
    normalized_group = str(group_name or "").strip()
    if not normalized_group:
        return False
    group = conn.execute(
        """
        SELECT id, program_id
        FROM msi_v2.groups
        WHERE lower(group_name) = lower(%s)
          AND status = 'active'
        ORDER BY id ASC
        LIMIT 1
        """,
        (normalized_group,),
    ).fetchone()
    if not group:
        return False
    conn.execute(
        """
        INSERT INTO msi_v2.group_teachers (group_id, teacher_id, role, status, assigned_at)
        VALUES (%s, %s, 'main', 'active', now())
        ON CONFLICT (group_id, teacher_id, role) DO UPDATE SET
            status = 'active',
            assigned_at = now()
        """,
        (int(group["id"]), int(teacher_id)),
    )
    subject = conn.execute(
        """
        SELECT subject_id
        FROM msi_v2.subject_programs
        WHERE id = %s
        LIMIT 1
        """,
        (int(group["program_id"]),),
    ).fetchone()
    if subject:
        upsert_teacher_subject(conn, int(teacher_id), int(subject["subject_id"]))
    return True


def activate_teacher_profile(conn, teacher_id, promotion_notes="", updated_at=""):
    conn.execute(
        """
        UPDATE msi_v2.teachers
        SET status = 'active',
            notes = COALESCE(NULLIF(%s, ''), notes),
            updated_at = COALESCE(NULLIF(%s, '')::timestamptz, now())
        WHERE id = %s
        """,
        (str(promotion_notes or "").strip(), updated_at, int(teacher_id)),
    )


def get_teacher_by_group_row(conn, group_name):
    return conn.execute(
        f"""
        SELECT {_teacher_select()}
        FROM msi_v2.teachers t
        JOIN msi_v2.group_teachers gt ON gt.teacher_id = t.id AND gt.status = 'active'
        JOIN msi_v2.groups g ON g.id = gt.group_id
        LEFT JOIN msi_v2.msi_staff staff ON staff.teacher_id = t.id
        LEFT JOIN msi_v2.teacher_profiles profile ON profile.teacher_id = t.id
        LEFT JOIN msi_v2.accounts account ON account.id = profile.account_id
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
        LEFT JOIN msi_v2.msi_staff staff ON staff.teacher_id = t.id
        LEFT JOIN msi_v2.teacher_profiles profile ON profile.teacher_id = t.id
        LEFT JOIN msi_v2.accounts account ON account.id = profile.account_id
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



def list_subject_options_for_teacher_rows(conn, teacher_id):
    """Active subjects offered to a teacher: all subjects when the teacher has
    no active subject assignment, otherwise only their assigned subjects."""
    return conn.execute(
        """
        SELECT DISTINCT s.id, s.subject_name AS name
        FROM msi_v2.subjects s
        LEFT JOIN msi_v2.teacher_subjects ts
          ON ts.subject_id = s.id
         AND ts.teacher_id = %s
         AND ts.status = 'active'
        WHERE s.status = 'active'
          AND (
            EXISTS (
                SELECT 1
                FROM msi_v2.teacher_subjects assigned
                WHERE assigned.teacher_id = %s
                  AND assigned.status = 'active'
            ) = false
            OR ts.teacher_id IS NOT NULL
          )
        ORDER BY s.subject_name
        """,
        (teacher_id, teacher_id),
    ).fetchall()


__all__ = [
    "list_teachers_rows",
    "get_teacher_login_row",
    "get_teacher_by_telegram_id",
    "get_teacher_auth_row_by_id",
    "list_teacher_ids_without_auth",
    "get_next_teacher_code",
    "get_next_teacher_login",
    "insert_teacher_auth",
    "update_teacher_password",
    "get_teacher_by_id_row",
    "insert_teacher_row",
    "insert_teacher_profile_row",
    "upsert_teacher_subject",
    "set_teacher_group_assignment",
    "activate_teacher_profile",
    "get_teacher_by_group_row",
    "get_teacher_by_full_name_row",
    "delete_teacher_by_group",
    "update_teacher_row_by_id",
    "delete_teacher_row_by_id",
    "list_subject_options_for_teacher_rows",
]
