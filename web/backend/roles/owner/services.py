"""Owner role service facade."""

from shared.identity.account_service import (  # noqa: F401
    detect_login_role,
    init_storage,
    verify_admin_credentials,
)
from shared.identity.account_service import (  # noqa: F401
    delete_teacher_by_id,
    list_teachers,
    upsert_teacher,
)

__all__ = [
    "delete_teacher_by_id",
    "detect_login_role",
    "init_storage",
    "list_teachers",
    "upsert_teacher",
    "verify_admin_credentials",
]

