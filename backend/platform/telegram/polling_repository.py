"""PostgreSQL advisory-lock persistence for Telegram polling leadership."""

from __future__ import annotations

from backend.core.database import connect_auth_db
from backend.core.unit_of_work import Connection


def try_acquire_polling_lock(lock_key: int) -> Connection | None:
    connection = connect_auth_db()
    try:
        row = connection.execute(
            "SELECT pg_try_advisory_lock(%s) AS acquired",
            (lock_key,),
        ).fetchone()
        connection.commit()
    except Exception:
        connection.close()
        raise
    if row and bool(row["acquired"]):
        return connection
    connection.close()
    return None


def release_polling_lock(connection: Connection | None, lock_key: int) -> None:
    if connection is None:
        return
    try:
        connection.execute(
            "SELECT pg_advisory_unlock(%s)",
            (lock_key,),
        )
        connection.commit()
    finally:
        connection.close()


__all__ = ["release_polling_lock", "try_acquire_polling_lock"]
