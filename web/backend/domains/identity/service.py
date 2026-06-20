"""Web-backend identity facade.

Shared login/account logic lives in ``shared.identity``. FastAPI session
helpers live in ``web.backend.utils``.
"""

from shared.identity.account_service import (  # noqa: F401
    detect_login_role,
    get_admin_by_telegram_user_id,
    get_student_by_telegram_user_id,
    link_admin_telegram_user,
    link_student_telegram_user,
    unlink_telegram_user_links,
    verify_admin_credentials,
    verify_student_credentials,
)
from web.backend.utils.telegram_auth import telegram_user_id_from_init_data  # noqa: F401

__all__ = [
    "detect_login_role",
    "get_admin_by_telegram_user_id",
    "get_student_by_telegram_user_id",
    "link_admin_telegram_user",
    "link_student_telegram_user",
    "telegram_user_id_from_init_data",
    "unlink_telegram_user_links",
    "verify_admin_credentials",
    "verify_student_credentials",
]
