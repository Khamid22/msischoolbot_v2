def upsert_meta(conn, key, value):
    conn.execute(
        """
        INSERT INTO app_meta (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (key, value),
    )


def get_meta(conn, key):
    row = conn.execute(
        "SELECT value FROM app_meta WHERE key = ?",
        (key,),
    ).fetchone()
    if not row:
        return ""
    return str(row["value"])


__all__ = ["upsert_meta", "get_meta"]
