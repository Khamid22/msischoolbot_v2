import os
import sqlite3

# Shared auth DB location for both web and telegram modules.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_AUTH_DB_PATH = os.path.join(_PROJECT_ROOT, "utils", "app_data.sqlite3")
_LEGACY_AUTH_DB_PATH = os.path.join(_PROJECT_ROOT, "web", "app_data.sqlite3")


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
    if not os.path.exists(_LEGACY_AUTH_DB_PATH):
        return

    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    try:
        os.replace(_LEGACY_AUTH_DB_PATH, db_path)
    except OSError:
        # Keep app running even if migration cannot move the file.
        return


def connect_auth_db():
    db_path = os.path.abspath(get_auth_db_path())
    _migrate_legacy_db_if_needed(db_path)

    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
