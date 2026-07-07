"""Temporary compatibility wrapper for database infrastructure.

Database connection ownership lives in ``backend.core.database``. Keep this
module until Alembic and legacy imports migrate fully to the core package path.

Temporary compatibility wrapper. Delete after all imports use
``backend.core.database``.
"""

from backend.core.database import (  # noqa: F401
    _PostgresConnectionWrapper,
    _PostgresCursorResult,
    _database_url,
    _env_float,
    _env_int,
    _get_pool,
    _is_postgres_database_url,
    _load_project_env_once,
    _open_new_connection,
    _pool_enabled,
    _pool_max,
    _pool_max_idle_seconds,
    _pool_min,
    _pool_putconn,
    _pool_timeout,
    _require_database_url,
    close_idle_pool_connections,
    connect_auth_db,
    get_db_backend,
    get_db_backend_for_connection,
)

__all__ = [
    "close_idle_pool_connections",
    "connect_auth_db",
    "get_db_backend",
    "get_db_backend_for_connection",
]
