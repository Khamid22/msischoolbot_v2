import asyncio
import html

from backend.identity.telegram_links import (
    get_admin_by_telegram_user_id,
    get_student_by_telegram_user_id,
)
from backend.identity.parent_accounts import parent_from_telegram_user_id


def escape(value):
    """Make text safe to put inside HTML messages (e.g. names with < or &)."""
    return html.escape(str(value or ""))


async def run_blocking(func, *args, **kwargs):
    """Run a synchronous (DB) call on a worker thread.

    The account lookups below use synchronous psycopg connections. Calling them
    directly inside an aiogram handler blocks the bot's event loop, so one slow
    query would stall updates for every user. to_thread keeps the loop free.
    """
    return await asyncio.to_thread(func, *args, **kwargs)


async def linked_student_from_user(user):
    """Return the student row linked to this Telegram user, or None."""
    telegram_user_id = getattr(user, "id", None)
    if not isinstance(telegram_user_id, int):
        return None
    try:
        return await run_blocking(get_student_by_telegram_user_id, telegram_user_id)
    except Exception:
        return None


async def linked_admin_from_user(user):
    """Return the admin row linked to this Telegram user, or None."""
    telegram_user_id = getattr(user, "id", None)
    if not isinstance(telegram_user_id, int):
        return None
    try:
        return await run_blocking(get_admin_by_telegram_user_id, telegram_user_id)
    except Exception:
        return None


async def linked_parent_from_user(user):
    """Return the parent client row linked to this Telegram user, or None."""
    telegram_user_id = getattr(user, "id", None)
    if not isinstance(telegram_user_id, int):
        return None
    try:
        return await run_blocking(parent_from_telegram_user_id, telegram_user_id)
    except Exception:
        return None
