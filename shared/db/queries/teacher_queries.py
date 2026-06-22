
def list_teachers_rows(conn):
    return conn.execute(
        """
        SELECT
            t.id,
            t.full_name,
            t.pay_rate,
            t.assigned_group,
            t.category,
            t.semester_stage,
            t.performance_score,
            t.supervised_lessons,
            t.igcse_evidence,
            t.promotion_notes,
            t.created_at,
            t.updated_at,
            a.login AS login,
            a.password AS password
        FROM teachers t
        LEFT JOIN teacher_auth a ON a.teacher_id = t.id
        ORDER BY lower(t.full_name) ASC, t.id ASC
        """
    ).fetchall()


# ── Teacher login credentials (teacher_auth) ──────────────────────────────────

def get_teacher_login_row(conn, login):
    return conn.execute(
        """
        SELECT
            t.id,
            t.full_name,
            t.assigned_group,
            a.login,
            a.password_hash
        FROM teachers t
        JOIN teacher_auth a ON a.teacher_id = t.id
        WHERE lower(a.login) = lower(%s)
        """,
        (login,),
    ).fetchone()


def get_teacher_auth_row_by_id(conn, teacher_id):
    return conn.execute(
        """
        SELECT teacher_id, login, password, password_hash
        FROM teacher_auth
        WHERE teacher_id = %s
        """,
        (teacher_id,),
    ).fetchone()


def list_teacher_ids_without_auth(conn):
    return conn.execute(
        """
        SELECT t.id
        FROM teachers t
        LEFT JOIN teacher_auth a ON a.teacher_id = t.id
        WHERE a.teacher_id IS NULL
        ORDER BY t.id ASC
        """
    ).fetchall()


def get_next_teacher_code(conn, prefix="TCH"):
    normalized_prefix = str(prefix or "TCH").strip().upper() or "TCH"
    rows = conn.execute(
        """
        SELECT login
        FROM teacher_auth
        WHERE upper(login) LIKE %s
        """,
        (f"{normalized_prefix}%",),
    ).fetchall()

    max_num = 0
    prefix_length = len(normalized_prefix)
    for row in rows:
        raw_login = str(row["login"] or "").strip().upper()
        if not raw_login.startswith(normalized_prefix):
            continue
        numeric_part = raw_login[prefix_length:]
        if not numeric_part.isdigit():
            continue
        max_num = max(max_num, int(numeric_part))

    return f"{normalized_prefix}{max_num + 1:03d}"


def insert_teacher_auth(conn, teacher_id, login, password, password_hash, updated_at):
    conn.execute(
        """
        INSERT INTO teacher_auth (teacher_id, login, password, password_hash, updated_at)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (teacher_id) DO NOTHING
        """,
        (teacher_id, login, password, password_hash, updated_at),
    )


def update_teacher_password(conn, teacher_id, plain_password, password_hash, updated_at):
    conn.execute(
        """
        UPDATE teacher_auth
        SET password = %s, password_hash = %s, updated_at = %s
        WHERE teacher_id = %s
        """,
        (plain_password, password_hash, updated_at, teacher_id),
    )


def get_teacher_by_id_row(conn, teacher_id):
    return conn.execute(
        """
        SELECT
            id,
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
            updated_at
        FROM teachers
        WHERE id = %s
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
    existing = get_teacher_by_group_row(conn, assigned_group)
    if existing:
        conn.execute(
            """
            UPDATE teachers
            SET
                full_name = %s,
                pay_rate = %s,
                assigned_group = %s,
                category = %s,
                semester_stage = %s,
                performance_score = %s,
                supervised_lessons = %s,
                igcse_evidence = %s,
                promotion_notes = %s,
                updated_at = %s
            WHERE id = %s
            """,
            (
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
                int(existing["id"]),
            ),
        )
        return

    conn.execute(
        """
        INSERT INTO teachers (
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
            updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
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
        ),
    )


def get_teacher_by_group_row(conn, group_name):
    return conn.execute(
        """
        SELECT id, full_name, pay_rate, assigned_group, category, semester_stage,
               performance_score, supervised_lessons, igcse_evidence, promotion_notes
        FROM teachers
        WHERE lower(assigned_group) = lower(%s)
        """,
        (group_name,),
    ).fetchone()


def get_teacher_by_full_name_row(conn, full_name):
    return conn.execute(
        """
        SELECT id, full_name, pay_rate, assigned_group, category, semester_stage,
               performance_score, supervised_lessons, igcse_evidence, promotion_notes
        FROM teachers
        WHERE lower(full_name) = lower(%s)
        ORDER BY id ASC
        LIMIT 1
        """,
        (full_name,),
    ).fetchone()


def delete_teacher_by_group(conn, group_name):
    conn.execute(
        """
        DELETE FROM teachers
        WHERE lower(assigned_group) = lower(%s)
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
        UPDATE teachers
        SET
            full_name = %s,
            pay_rate = %s,
            assigned_group = %s,
            category = %s,
            semester_stage = %s,
            performance_score = %s,
            supervised_lessons = %s,
            igcse_evidence = %s,
            promotion_notes = %s,
            updated_at = %s
        WHERE id = %s
        """,
        (
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
            teacher_id,
        ),
    )


def delete_teacher_row_by_id(conn, teacher_id):
    conn.execute(
        """
        DELETE FROM teachers
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
