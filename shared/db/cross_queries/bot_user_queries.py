def get_bot_users_count(conn):
    row = conn.execute("SELECT COUNT(*) AS total FROM bot_users").fetchone()
    return int(row["total"] if row else 0)


def upsert_bot_user(conn, user_id, username, first_name, last_name, now):
    conn.execute(
        """
        INSERT INTO bot_users (
            telegram_user_id,
            username,
            first_name,
            last_name,
            created_at,
            updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT(telegram_user_id) DO UPDATE SET
            username = excluded.username,
            first_name = excluded.first_name,
            last_name = excluded.last_name,
            updated_at = excluded.updated_at
        """,
        (user_id, username, first_name, last_name, now, now),
    )


__all__ = [
    "get_bot_users_count",
    "upsert_bot_user",
]
