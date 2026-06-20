
def list_teachers_rows(conn):
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
        ORDER BY lower(full_name) ASC, id ASC
        """
    ).fetchall()


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
    "get_teacher_by_id_row",
    "insert_teacher_row",
    "get_teacher_by_group_row",
    "get_teacher_by_full_name_row",
    "delete_teacher_by_group",
    "update_teacher_row_by_id",
    "delete_teacher_row_by_id",
]
