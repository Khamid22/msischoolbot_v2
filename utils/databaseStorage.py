import os
import sqlite3

# Shared auth DB location for both web and telegram modules.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_AUTH_DB_PATH = os.path.join(_PROJECT_ROOT, "utils", "app_data.sqlite3")
_LEGACY_AUTH_DB_PATHS = (
    os.path.join(_PROJECT_ROOT, "app", "app_data.sqlite3"),
    os.path.join(_PROJECT_ROOT, "web", "app_data.sqlite3"),
)


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
            from app.extensions import db
        except ImportError:
            from extensions import db

        raw_conn = db.engine.raw_connection()
    except Exception:
        return None

    driver_connection = getattr(raw_conn, "driver_connection", None)
    if driver_connection is None:
        driver_connection = getattr(raw_conn, "connection", None)
    if driver_connection is not None and hasattr(driver_connection, "row_factory"):
        driver_connection.row_factory = sqlite3.Row

    raw_conn.execute("PRAGMA foreign_keys = ON")
    return raw_conn


def get_auth_db_path():
    custom_path = os.environ.get("AUTH_DB_PATH", "").strip()
    if custom_path:
        return custom_path
    return _DEFAULT_AUTH_DB_PATH


def _migrate_legacy_db_if_needed(db_path):
    if db_path != _DEFAULT_AUTH_DB_PATH:
        return
    if os.path.exists(db_path):
        return

    legacy_path = next((path for path in _LEGACY_AUTH_DB_PATHS if os.path.exists(path)), "")
    if not legacy_path:
        return

    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    try:
        os.replace(legacy_path, db_path)
    except OSError:
        # Keep app running even if migration cannot move the file.
        return


def connect_auth_db():
    sqlalchemy_conn = _connect_via_flask_sqlalchemy()
    if sqlalchemy_conn is not None:
        return sqlalchemy_conn

    db_path = os.path.abspath(get_auth_db_path())
    _migrate_legacy_db_if_needed(db_path)

    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
