def upsert_meta(conn, key, value):
    conn.execute(
        """
        INSERT INTO msi_v2.app_settings (key, value)
        VALUES (%s, %s)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = now()
        """,
        (key, value),
    )


def get_meta(conn, key):
    row = conn.execute(
        "SELECT value FROM msi_v2.app_settings WHERE key = %s",
        (key,),
    ).fetchone()
    if not row:
        return ""
    return str(row["value"])


__all__ = ["upsert_meta", "get_meta"]
