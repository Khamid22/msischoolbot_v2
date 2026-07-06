"""Web-backend identity facade.

Shared login/account logic lives in ``backend.identity``. FastAPI session
helpers live in ``backend.utils``.
"""

from backend.identity.account_service import (  # noqa: F401
    get_admin_by_telegram_user_id,
    get_student_by_telegram_user_id,
    link_admin_telegram_user,
    link_student_telegram_user,
    unlink_telegram_user_links,
)
from backend.integrations.telegram.init_data import telegram_user_id_from_init_data  # noqa: F401

__all__ = [
    "get_admin_by_telegram_user_id",
    "get_student_by_telegram_user_id",
    "link_admin_telegram_user",
    "link_student_telegram_user",
    "telegram_user_id_from_init_data",
    "unlink_telegram_user_links",
]
