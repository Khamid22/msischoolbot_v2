"""SQL ownership for staff Telegram identity links."""

from __future__ import annotations

from typing import Any


def get_active_link_for_account(conn: Any, account_id: int) -> Any:
    return conn.execute(
        """
        SELECT id, telegram_user_id, telegram_username, linked_at
        FROM msi_v2.account_telegram_links
        WHERE account_id = %s AND status = 'active'
        ORDER BY linked_at DESC, id DESC
        LIMIT 1
        """,
        (int(account_id),),
    ).fetchone()


def get_active_link_for_identity(
    conn: Any,
    telegram_user_id: int,
    *,
    for_update: bool = False,
) -> Any:
    lock = "FOR UPDATE" if for_update else ""
    return conn.execute(
        f"""
        SELECT id, account_id
        FROM msi_v2.account_telegram_links
        WHERE telegram_user_id = %s AND status = 'active'
        LIMIT 1
        {lock}
        """,
        (int(telegram_user_id),),
    ).fetchone()


def revoke_other_active_links(
    conn: Any,
    *,
    account_id: int,
    keep_telegram_user_id: int,
) -> None:
    conn.execute(
        """
        UPDATE msi_v2.account_telegram_links
        SET status = 'revoked', revoked_at = now(), updated_at = now()
        WHERE account_id = %s AND status = 'active'
          AND telegram_user_id <> %s
        """,
        (int(account_id), int(keep_telegram_user_id)),
    )


def refresh_active_link(conn: Any, *, link_id: int, username: str) -> None:
    conn.execute(
        """
        UPDATE msi_v2.account_telegram_links
        SET telegram_username = NULLIF(%s, ''), linked_at = now(),
            revoked_at = NULL, updated_at = now()
        WHERE id = %s
        """,
        (username, int(link_id)),
    )


def insert_active_link(
    conn: Any,
    *,
    account_id: int,
    telegram_user_id: int,
    username: str,
) -> bool:
    row = conn.execute(
        """
        INSERT INTO msi_v2.account_telegram_links (
            account_id, telegram_user_id, telegram_username,
            linked_at, status, revoked_at, updated_at
        ) VALUES (%s, %s, NULLIF(%s, ''), now(), 'active', NULL, now())
        ON CONFLICT (telegram_user_id) WHERE status = 'active' DO NOTHING
        RETURNING id
        """,
        (int(account_id), int(telegram_user_id), username),
    ).fetchone()
    return bool(row)


def requeue_waiting_recruitment_notifications(conn: Any, account_id: int) -> None:
    conn.execute(
        """
        UPDATE msi_v2.teacher_recruitment_notifications
        SET telegram_status = 'pending', telegram_next_attempt_at = now(),
            telegram_last_error = '', updated_at = now()
        WHERE recipient_account_id = %s
          AND telegram_status = 'waiting_link'
          AND deliver_at <= now()
        """,
        (int(account_id),),
    )


def revoke_active_links(conn: Any, account_id: int) -> list[int]:
    rows = conn.execute(
        """
        UPDATE msi_v2.account_telegram_links
        SET status = 'revoked', revoked_at = now(), updated_at = now()
        WHERE account_id = %s AND status = 'active'
        RETURNING telegram_user_id
        """,
        (int(account_id),),
    ).fetchall()
    return [int(row["telegram_user_id"]) for row in rows]


__all__ = [name for name in globals() if not name.startswith("_")]
