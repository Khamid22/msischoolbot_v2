"""Admin-related SQL query helpers."""


def get_admin_id_by_login(conn, login):
    return conn.execute(
        "SELECT id FROM admins WHERE lower(login) = lower(?)",
        (login,),
    ).fetchone()


def insert_owner_admin(conn, login, password_hash, created_at):
    conn.execute(
        """
        INSERT INTO admins (login, password_hash, role, is_owner, created_at)
        VALUES (?, ?, ?, 1, ?)
        """,
        (login, password_hash, "owner", created_at),
    )


def get_admin_credentials_row(conn, login):
    return conn.execute(
        """
        SELECT id, login, password_hash, role, is_owner
        FROM admins
        WHERE lower(login) = lower(?)
        """,
        (login,),
    ).fetchone()


def get_admin_row_by_id(conn, admin_id):
    return conn.execute(
        """
        SELECT id, login, role, is_owner, telegram_user_id
        FROM admins
        WHERE id = ?
        """,
        (admin_id,),
    ).fetchone()


def get_admin_by_telegram_id(conn, telegram_user_id):
    return conn.execute(
        """
        SELECT id, login, role, is_owner
        FROM admins
        WHERE telegram_user_id = ?
        """,
        (telegram_user_id,),
    ).fetchone()


def clear_admin_telegram_user_conflicts(conn, telegram_user_id, admin_id = None):
    if isinstance(admin_id, int) and admin_id > 0:
        conn.execute(
            """
            UPDATE admins
            SET telegram_user_id = NULL
            WHERE telegram_user_id = ?
              AND id != ?
            """,
            (telegram_user_id, admin_id),
        )
        return

    conn.execute(
        """
        UPDATE admins
        SET telegram_user_id = NULL
        WHERE telegram_user_id = ?
        """,
        (telegram_user_id,),
    )


def update_admin_telegram_user(conn, telegram_user_id, admin_id):
    conn.execute(
        """
        UPDATE admins
        SET telegram_user_id = ?
        WHERE id = ?
        """,
        (telegram_user_id, admin_id),
    )


__all__ = [
    "get_admin_id_by_login",
    "insert_owner_admin",
    "get_admin_credentials_row",
    "get_admin_row_by_id",
    "get_admin_by_telegram_id",
    "clear_admin_telegram_user_conflicts",
    "update_admin_telegram_user",
]
