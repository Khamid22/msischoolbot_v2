"""Core database access helpers for MSI LMS Portal."""

from __future__ import annotations

import atexit
import os
import threading

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PROJECT_DOTENV_PATH = os.path.join(_PROJECT_ROOT, ".env")


def _load_project_env_once() -> None:
    if getattr(_load_project_env_once, "_loaded", False):
        return
    setattr(_load_project_env_once, "_loaded", True)
    try:
        from dotenv import load_dotenv
    except Exception:
        return
    load_dotenv(dotenv_path=_PROJECT_DOTENV_PATH)


def _database_url() -> str:
    _load_project_env_once()
    return (
        os.environ.get("DATABASE_URL", "").strip()
        or os.environ.get("POSTGRES_URL", "").strip()
    )


def _is_postgres_database_url(url: str) -> bool:
    normalized = str(url or "").strip().lower()
    return normalized.startswith("postgres://") or normalized.startswith(
        "postgresql://"
    )


def _require_database_url() -> str:
    database_url = _database_url()
    if not _is_postgres_database_url(database_url):
        raise RuntimeError(
            "PostgreSQL is required. Set DATABASE_URL to a postgresql:// URL."
        )
    return database_url


def get_db_backend() -> str:
    _require_database_url()
    return "postgres"


class _PostgresCursorResult:
    """Thin view over a psycopg cursor."""

    def __init__(self, cursor):
        self._cursor = cursor
        raw_rowcount = getattr(cursor, "rowcount", None)
        try:
            self.rowcount = int(raw_rowcount) if raw_rowcount is not None else -1
        except (TypeError, ValueError):
            self.rowcount = -1

    def fetchone(self):
        return self._cursor.fetchone() if self._cursor is not None else None

    def fetchall(self):
        return self._cursor.fetchall() if self._cursor is not None else []


class _PostgresConnectionWrapper:
    db_backend = "postgres"

    def __init__(self, connection, *, release=None):
        self._connection = connection
        self._release = release
        self._closed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        self.close()
        return False

    def execute(self, sql, params=None):
        cursor = self._connection.cursor()
        cursor.execute(sql, tuple(params) if params is not None else None)
        return _PostgresCursorResult(cursor)

    def executemany(self, sql, seq_of_params):
        cursor = self._connection.cursor()
        cursor.executemany(sql, list(seq_of_params))
        return _PostgresCursorResult(cursor)

    def commit(self):
        self._connection.commit()

    def rollback(self):
        self._connection.rollback()

    def close(self):
        if self._closed:
            return
        self._closed = True
        if self._release is not None:
            self._release(self._connection)
        else:
            self._connection.close()


def get_db_backend_for_connection(conn) -> str:
    backend = getattr(conn, "db_backend", "")
    if str(backend).strip().casefold() != "postgres":
        raise RuntimeError("Only PostgreSQL connections are supported.")
    return "postgres"


_PG_POOL = None
_PG_POOL_URL = ""
_PG_POOL_LOCK = threading.Lock()


def _env_int(name: str, default: int) -> int:
    try:
        return int(str(os.environ.get(name, "") or "").strip() or default)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(str(os.environ.get(name, "") or "").strip() or default)
    except ValueError:
        return default


def _pool_enabled() -> bool:
    flag = str(os.environ.get("DB_POOL_DISABLE", "") or "").strip().casefold()
    return flag not in {"1", "true", "yes", "on"}


def _pool_min() -> int:
    return max(0, _env_int("DB_POOL_MIN", 2))


def _pool_max() -> int:
    return max(1, _env_int("DB_POOL_MAX", 20))


def _pool_timeout() -> float:
    return max(1.0, _env_float("DB_POOL_TIMEOUT", 10.0))


def _pool_max_idle_seconds() -> int:
    return max(1, _env_int("DB_POOL_MAX_IDLE_SECONDS", 300))


def _open_new_connection(database_url: str):
    try:
        import psycopg
        from psycopg.rows import dict_row
    except Exception as exc:
        raise RuntimeError(
            "PostgreSQL backend requires `psycopg` package. "
            "Install dependencies from requirements.txt."
        ) from exc

    connection = psycopg.connect(database_url, row_factory=dict_row)
    connection.autocommit = False
    return connection


def _get_pool(database_url: str):
    global _PG_POOL, _PG_POOL_URL
    if _PG_POOL is not None and _PG_POOL_URL == database_url:
        return _PG_POOL
    with _PG_POOL_LOCK:
        if _PG_POOL is not None and _PG_POOL_URL == database_url:
            return _PG_POOL
        if _PG_POOL is not None:
            try:
                _PG_POOL.close()
            except Exception:
                pass
            _PG_POOL = None
        try:
            from psycopg_pool import ConnectionPool
            from psycopg.rows import dict_row
        except Exception as exc:
            raise RuntimeError(
                "Bounded pooling requires `psycopg_pool`. Install dependencies "
                "from requirements.txt, or set DB_POOL_DISABLE=1."
            ) from exc

        pool = ConnectionPool(
            database_url,
            min_size=_pool_min(),
            max_size=_pool_max(),
            timeout=_pool_timeout(),
            max_idle=float(_pool_max_idle_seconds()),
            kwargs={"autocommit": False, "row_factory": dict_row},
            open=False,
        )
        pool.open(wait=False)
        _PG_POOL = pool
        _PG_POOL_URL = database_url
        return _PG_POOL


def _pool_putconn(pool, connection) -> None:
    try:
        pool.putconn(connection)
    except Exception:
        try:
            connection.close()
        except Exception:
            pass


def close_idle_pool_connections() -> None:
    """Close the pool and all its connections."""
    global _PG_POOL, _PG_POOL_URL
    with _PG_POOL_LOCK:
        pool = _PG_POOL
        _PG_POOL = None
        _PG_POOL_URL = ""
    if pool is not None:
        try:
            pool.close()
        except Exception:
            pass


def connect_auth_db():
    database_url = _require_database_url()
    if not _pool_enabled():
        return _PostgresConnectionWrapper(_open_new_connection(database_url))

    pool = _get_pool(database_url)
    connection = pool.getconn()
    return _PostgresConnectionWrapper(
        connection, release=lambda conn: _pool_putconn(pool, conn)
    )


connect = connect_auth_db


def connect_db():
    """Return the primary PostgreSQL connection wrapper used by domain queries."""
    return connect_auth_db()


atexit.register(close_idle_pool_connections)


__all__ = [
    "close_idle_pool_connections",
    "connect",
    "connect_auth_db",
    "connect_db",
    "get_db_backend",
    "get_db_backend_for_connection",
]
