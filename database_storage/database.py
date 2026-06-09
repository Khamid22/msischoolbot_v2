import os
import re

# PostgreSQL is the only supported application database.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PROJECT_DOTENV_PATH = os.path.join(_PROJECT_ROOT, ".env")


def _load_project_env_once():
    if getattr(_load_project_env_once, "_loaded", False):
        return
    setattr(_load_project_env_once, "_loaded", True)
    try:
        from dotenv import load_dotenv
    except Exception:
        return
    load_dotenv(dotenv_path=_PROJECT_DOTENV_PATH)


def _database_url():
    _load_project_env_once()
    return (
        os.environ.get("DATABASE_URL", "").strip()
        or os.environ.get("POSTGRES_URL", "").strip()
    )


def _is_postgres_database_url(url):
    normalized = str(url or "").strip().lower()
    return normalized.startswith("postgres://") or normalized.startswith(
        "postgresql://"
    )


def _require_database_url():
    database_url = _database_url()
    if not _is_postgres_database_url(database_url):
        raise RuntimeError(
            "PostgreSQL is required. Set DATABASE_URL to a postgresql:// URL."
        )
    return database_url


def get_db_backend():
    _require_database_url()
    return "postgres"


def _normalize_sqlalchemy_database_url(url):
    normalized = str(url or "").strip()
    if normalized.startswith("postgres://"):
        normalized = "postgresql+psycopg://" + normalized[len("postgres://") :]
    elif normalized.startswith("postgresql://"):
        normalized = "postgresql+psycopg://" + normalized[len("postgresql://") :]
    return normalized


def get_sqlalchemy_database_uri():
    return _normalize_sqlalchemy_database_url(_require_database_url())


def _sql_to_postgres(sql):
    text = str(sql or "")
    text = re.sub(r"\s+COLLATE\s+NOCASE\b", "", text, flags=re.IGNORECASE)
    if text.strip().casefold() == "select last_insert_rowid()":
        return "SELECT LASTVAL()"

    out = []
    in_single = False
    index = 0
    length = len(text)
    while index < length:
        char = text[index]
        if char == "'":
            out.append(char)
            if in_single and index + 1 < length and text[index + 1] == "'":
                out.append("'")
                index += 2
                continue
            in_single = not in_single
            index += 1
            continue
        if char == "?" and not in_single:
            out.append("%s")
            index += 1
            continue
        out.append(char)
        index += 1
    return "".join(out)


class _CompatRow:
    def __init__(self, column_names, values):
        self._column_names = tuple(column_names)
        self._values = tuple(values)
        self._index_by_name = {
            str(column_name): position
            for position, column_name in enumerate(self._column_names)
        }

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return self._values[self._index_by_name[str(key)]]

    def __iter__(self):
        return iter(self._values)

    def __len__(self):
        return len(self._values)

    def get(self, key, default=None):
        position = self._index_by_name.get(str(key))
        if position is None:
            return default
        return self._values[position]

    def keys(self):
        return self._column_names

    def values(self):
        return self._values

    def items(self):
        return tuple(
            (name, self._values[position])
            for position, name in enumerate(self._column_names)
        )


class _PostgresCursorResult:
    def __init__(self, cursor, *, lastrowid=None):
        self._cursor = cursor
        self.lastrowid = lastrowid
        raw_rowcount = getattr(cursor, "rowcount", None)
        try:
            self.rowcount = int(raw_rowcount) if raw_rowcount is not None else -1
        except (TypeError, ValueError):
            self.rowcount = -1
        self._column_names = tuple(
            str(getattr(description, "name", description[0]))
            for description in (cursor.description or [])
        )

    def _convert(self, row):
        if row is None:
            return None
        if not self._column_names:
            return row
        return _CompatRow(self._column_names, row)

    def fetchone(self):
        if self._cursor is None:
            return None
        return self._convert(self._cursor.fetchone())

    def fetchall(self):
        if self._cursor is None:
            return []
        return [self._convert(row) for row in self._cursor.fetchall()]


class _PostgresConnectionWrapper:
    db_backend = "postgres"

    def __init__(self, connection):
        self._connection = connection

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        self.close()
        return False

    def _infer_lastrowid(self):
        try:
            with self._connection.cursor() as cursor:
                cursor.execute("SELECT LASTVAL()")
                row = cursor.fetchone()
        except Exception:
            return None
        if not row:
            return None
        try:
            return int(row[0])
        except (TypeError, ValueError):
            return None

    def execute(self, sql, params=None):
        translated_sql = _sql_to_postgres(sql)
        normalized_params = tuple(params or ())
        cursor = self._connection.cursor()
        cursor.execute(translated_sql, normalized_params)

        lastrowid = None
        if translated_sql.lstrip().upper().startswith("INSERT INTO "):
            lastrowid = self._infer_lastrowid()
        return _PostgresCursorResult(cursor, lastrowid=lastrowid)

    def executemany(self, sql, seq_of_params):
        translated_sql = _sql_to_postgres(sql)
        cursor = self._connection.cursor()
        cursor.executemany(translated_sql, seq_of_params)
        return _PostgresCursorResult(cursor)

    def commit(self):
        self._connection.commit()

    def rollback(self):
        self._connection.rollback()

    def close(self):
        self._connection.close()


def get_db_backend_for_connection(conn):
    backend = getattr(conn, "db_backend", "")
    if str(backend).strip().casefold() != "postgres":
        raise RuntimeError("Only PostgreSQL connections are supported.")
    return "postgres"


def _connect_via_flask_sqlalchemy():
    try:
        from flask import current_app, has_app_context
    except Exception:
        return None

    if not has_app_context():
        return None

    try:
        if "sqlalchemy" not in getattr(current_app, "extensions", {}):
            return None
    except RuntimeError:
        return None

    try:
        try:
            from web.backend.extensions import db
        except ImportError:
            from extensions import db

        raw_conn = db.engine.raw_connection()
    except Exception:
        return None

    return _PostgresConnectionWrapper(raw_conn)


def connect_auth_db():
    sqlalchemy_conn = _connect_via_flask_sqlalchemy()
    if sqlalchemy_conn is not None:
        return sqlalchemy_conn

    try:
        import psycopg
    except Exception as exc:
        raise RuntimeError(
            "PostgreSQL backend requires `psycopg` package. "
            "Install dependencies from requirements.txt."
        ) from exc

    connection = psycopg.connect(_require_database_url())
    connection.autocommit = False
    return _PostgresConnectionWrapper(connection)
