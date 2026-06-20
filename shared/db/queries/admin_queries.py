"""Admin-related SQL query helpers."""


def get_admin_id_by_login(conn, login):
    return conn.execute(
        "SELECT id FROM admins WHERE lower(login) = lower(%s)",
        (login,),
    ).fetchone()


def insert_owner_admin(conn, login, password_hash, created_at):
    conn.execute(
        """
        INSERT INTO admins (login, password_hash, role, is_owner, created_at)
        VALUES (%s, %s, %s, 1, %s)
        """,
        (login, password_hash, "owner", created_at),
    )


def insert_parent_admin(conn, login, password_hash, created_at):
    row = conn.execute(
        """
        INSERT INTO admins (login, password_hash, role, is_owner, created_at)
        VALUES (%s, %s, %s, 0, %s)
        RETURNING id
        """,
        (login, password_hash, "parent", created_at),
    ).fetchone()
    return int(row["id"]) if row else 0


def get_admin_credentials_row(conn, login):
    return conn.execute(
        """
        SELECT id, login, password_hash, role, is_owner
        FROM admins
        WHERE lower(login) = lower(%s)
        """,
        (login,),
    ).fetchone()


def get_admin_row_by_id(conn, admin_id):
    return conn.execute(
        """
        SELECT id, login, role, is_owner, telegram_user_id
        FROM admins
        WHERE id = %s
        """,
        (admin_id,),
    ).fetchone()


def get_parent_admin_row(conn, admin_id):
    return conn.execute(
        """
        SELECT id, login, role, is_owner, telegram_user_id, created_at
        FROM admins
        WHERE id = %s
          AND lower(role) = 'parent'
        """,
        (admin_id,),
    ).fetchone()


def list_parent_admin_rows(conn):
    return conn.execute(
        """
        SELECT id, login, role, is_owner, telegram_user_id, created_at
        FROM admins
        WHERE lower(role) = 'parent'
        ORDER BY lower(login) ASC, id ASC
        """
    ).fetchall()


def get_admin_by_telegram_id(conn, telegram_user_id):
    return conn.execute(
        """
        SELECT id, login, role, is_owner
        FROM admins
        WHERE telegram_user_id = %s
        """,
        (telegram_user_id,),
    ).fetchone()


def clear_admin_telegram_user_conflicts(conn, telegram_user_id, admin_id = None):
    if isinstance(admin_id, int) and admin_id > 0:
        conn.execute(
            """
            UPDATE admins
            SET telegram_user_id = NULL
            WHERE telegram_user_id = %s
              AND id != %s
            """,
            (telegram_user_id, admin_id),
        )
        return

    conn.execute(
        """
        UPDATE admins
        SET telegram_user_id = NULL
        WHERE telegram_user_id = %s
        """,
        (telegram_user_id,),
    )


def update_admin_telegram_user(conn, telegram_user_id, admin_id):
    conn.execute(
        """
        UPDATE admins
        SET telegram_user_id = %s
        WHERE id = %s
        """,
        (telegram_user_id, admin_id),
    )


__all__ = [
    "get_admin_id_by_login",
    "insert_owner_admin",
    "insert_parent_admin",
    "get_admin_credentials_row",
    "get_admin_row_by_id",
    "get_parent_admin_row",
    "list_parent_admin_rows",
    "get_admin_by_telegram_id",
    "clear_admin_telegram_user_conflicts",
    "update_admin_telegram_user",
]
