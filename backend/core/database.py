"""Core database access helpers for MSI LMS Portal.

DB-1 keeps the physical PostgreSQL schema and the legacy database package in
place. This module is the clean import path for new domain query modules while
wrapping the already-working connection/pool implementation.
"""

from database.database import (
    close_idle_pool_connections,
    connect_auth_db,
    get_db_backend,
    get_db_backend_for_connection,
)
from backend.identity.common import connect


def connect_db():
    """Return the primary PostgreSQL connection wrapper used by domain queries."""
    return connect_auth_db()


__all__ = [
    "close_idle_pool_connections",
    "connect",
    "connect_auth_db",
    "connect_db",
    "get_db_backend",
    "get_db_backend_for_connection",
]
