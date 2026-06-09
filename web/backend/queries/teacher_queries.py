
def list_teachers_rows(conn):
    return conn.execute(
        """
        SELECT
            id,
            full_name,
            pay_rate,
            assigned_group,
            created_at,
            updated_at
        FROM teachers
        ORDER BY full_name COLLATE NOCASE ASC, id ASC
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
            created_at,
            updated_at
        FROM teachers
        WHERE id = ?
        """,
        (teacher_id,),
    ).fetchone()


def insert_teacher_row(conn, full_name, pay_rate, assigned_group, created_at, updated_at):
    existing = get_teacher_by_group_row(conn, assigned_group)
    if existing:
        conn.execute(
            """
            UPDATE teachers
            SET
                full_name = ?,
                pay_rate = ?,
                assigned_group = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                full_name,
                pay_rate,
                assigned_group,
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
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (full_name, pay_rate, assigned_group, created_at, updated_at),
    )


def get_teacher_by_group_row(conn, group_name):
    return conn.execute(
        """
        SELECT id, full_name, pay_rate, assigned_group
        FROM teachers
        WHERE lower(assigned_group) = lower(?)
        """,
        (group_name,),
    ).fetchone()


def get_teacher_by_full_name_row(conn, full_name):
    return conn.execute(
        """
        SELECT id, full_name, pay_rate, assigned_group
        FROM teachers
        WHERE lower(full_name) = lower(?)
        ORDER BY id ASC
        LIMIT 1
        """,
        (full_name,),
    ).fetchone()


def delete_teacher_by_group(conn, group_name):
    conn.execute(
        """
        DELETE FROM teachers
        WHERE lower(assigned_group) = lower(?)
        """,
        (group_name,),
    )


def update_teacher_row_by_id(conn, teacher_id, full_name, pay_rate, assigned_group, updated_at):
    conn.execute(
        """
        UPDATE teachers
        SET
            full_name = ?,
            pay_rate = ?,
            assigned_group = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (full_name, pay_rate, assigned_group, updated_at, teacher_id),
    )


def delete_teacher_row_by_id(conn, teacher_id):
    conn.execute(
        """
        DELETE FROM teachers
        WHERE id = ?
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
