"""Compatibility imports for Telegram WebApp ``initData`` verification.

Runtime code may continue importing from this legacy utility path while the
implementation lives in ``backend.integrations.telegram.init_data``.
"""

from backend.integrations.telegram.init_data import (
    telegram_user_from_init_data,
    telegram_user_id_from_init_data,
    verify_telegram_init_data,
)

__all__ = [
    "verify_telegram_init_data",
    "telegram_user_id_from_init_data",
    "telegram_user_from_init_data",
]
