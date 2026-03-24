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


__all__ = [
    "get_admin_id_by_login",
    "insert_owner_admin",
    "get_admin_credentials_row",
]
