"""Stable database connection exports.

Schema ownership lives in Alembic and SQL ownership lives in domain query
modules under :mod:`backend.domains`.
"""

from backend.core.database import connect_auth_db, get_db_backend

__all__ = [
    "connect_auth_db",
    "get_db_backend",
]
