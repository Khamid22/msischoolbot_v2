import html

from backend.identity.account_service import (
    get_admin_by_telegram_user_id,
    get_student_by_telegram_user_id,
)
from backend.identity.parent_accounts import parent_from_telegram_user_id


def escape(value):
    """Make text safe to put inside HTML messages (e.g. names with < or &)."""
    return html.escape(str(value or ""))


def linked_student_from_user(user):
    """Return the student row linked to this Telegram user, or None."""
    telegram_user_id = getattr(user, "id", None)
    if not isinstance(telegram_user_id, int):
        return None
    try:
        return get_student_by_telegram_user_id(telegram_user_id)
    except Exception:
        return None


def linked_admin_from_user(user):
    """Return the admin row linked to this Telegram user, or None."""
    telegram_user_id = getattr(user, "id", None)
    if not isinstance(telegram_user_id, int):
        return None
    try:
        return get_admin_by_telegram_user_id(telegram_user_id)
    except Exception:
        return None


def linked_parent_from_user(user):
    """Return the parent client row linked to this Telegram user, or None."""
    telegram_user_id = getattr(user, "id", None)
    if not isinstance(telegram_user_id, int):
        return None
    try:
        return parent_from_telegram_user_id(telegram_user_id)
    except Exception:
        return None
