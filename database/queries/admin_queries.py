"""Admin-related SQL query helpers."""


def get_admin_id_by_login(conn, login):
    return conn.execute(
        "SELECT COALESCE(legacy_admin_id, id) AS id FROM msi_v2.msi_staff WHERE lower(login) = lower(%s)",
        (login,),
    ).fetchone()


def insert_owner_admin(conn, login, password_hash, created_at):
    conn.execute(
        """
        INSERT INTO msi_v2.msi_staff (login, password_hash, role, status)
        VALUES (%s, %s, 'owner', 'active')
        """,
        (login, password_hash),
    )


def get_admin_credentials_row(conn, login):
    return conn.execute(
        """
        SELECT COALESCE(legacy_admin_id, id) AS id, login, password_hash, role,
               CASE WHEN lower(role) = 'owner' THEN 1 ELSE 0 END AS is_owner,
               CASE WHEN status = 'disabled' THEN 1 ELSE 0 END AS disabled
        FROM msi_v2.msi_staff
        WHERE lower(login) = lower(%s)
        """,
        (login,),
    ).fetchone()


def get_admin_row_by_id(conn, admin_id):
    return conn.execute(
        """
        SELECT COALESCE(legacy_admin_id, id) AS id, login, role,
               CASE WHEN lower(role) = 'owner' THEN 1 ELSE 0 END AS is_owner,
               telegram_user_id
        FROM msi_v2.msi_staff
        WHERE COALESCE(legacy_admin_id, id) = %s
        """,
        (admin_id,),
    ).fetchone()


def get_admin_by_telegram_id(conn, telegram_user_id):
    return conn.execute(
        """
        SELECT COALESCE(legacy_admin_id, id) AS id, login, role,
               CASE WHEN lower(role) = 'owner' THEN 1 ELSE 0 END AS is_owner
        FROM msi_v2.msi_staff
        WHERE telegram_user_id = %s
        """,
        (telegram_user_id,),
    ).fetchone()


def clear_admin_telegram_user_conflicts(conn, telegram_user_id, admin_id = None):
    if isinstance(admin_id, int) and admin_id > 0:
        conn.execute(
            """
            UPDATE msi_v2.msi_staff
            SET telegram_user_id = NULL
            WHERE telegram_user_id = %s
              AND COALESCE(legacy_admin_id, id) != %s
            """,
            (telegram_user_id, admin_id),
        )
        return

    conn.execute(
        """
        UPDATE msi_v2.msi_staff
        SET telegram_user_id = NULL
        WHERE telegram_user_id = %s
        """,
        (telegram_user_id,),
    )


def update_admin_telegram_user(conn, telegram_user_id, admin_id):
    conn.execute(
        """
        UPDATE msi_v2.msi_staff
        SET telegram_user_id = %s
        WHERE COALESCE(legacy_admin_id, id) = %s
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
