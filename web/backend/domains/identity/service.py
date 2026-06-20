"""Web-backend identity facade.

Shared login/account logic lives in ``shared.identity``. Flask-specific session
helpers live in ``web.backend.auth`` and ``web.backend.utils``.
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
from web.backend.auth.policies import is_authenticated_session  # noqa: F401
from web.backend.auth.session import (  # noqa: F401
    configure_login_manager,
    load_portal_user,
)
from web.backend.utils.telegram_auth import telegram_user_id_from_init_data  # noqa: F401

__all__ = [
    "configure_login_manager",
    "detect_login_role",
    "get_admin_by_telegram_user_id",
    "get_student_by_telegram_user_id",
    "is_authenticated_session",
    "link_admin_telegram_user",
    "link_student_telegram_user",
    "load_portal_user",
    "telegram_user_id_from_init_data",
    "unlink_telegram_user_links",
    "verify_admin_credentials",
    "verify_student_credentials",
]
