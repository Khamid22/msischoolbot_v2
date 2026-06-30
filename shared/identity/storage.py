"""Identity storage bootstrap and owner seeding."""

import logging
import os
from pathlib import Path

from werkzeug.security import generate_password_hash

from shared.db import queries
from shared.identity.common import DB_LOCK, connect, utc_now_iso

OWNER_LOGIN = (os.environ.get("OWNER_ADMIN_LOGIN", "admin") or "admin").strip()
OWNER_PASSWORD = (os.environ.get("OWNER_ADMIN_PASSWORD", "") or "").strip()

_STORAGE_READY = False
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_V2_SCHEMA_SQL = _PROJECT_ROOT / "scripts" / "rebuild_database_v2.sql"


def ensure_clean_v2_schema(conn):
    """Create the clean msi_v2 schema if the deployment includes the SQL file."""
    if not _V2_SCHEMA_SQL.exists():
        logging.warning("Clean database schema file is missing: %s", _V2_SCHEMA_SQL)
        return
    conn.execute(_V2_SCHEMA_SQL.read_text(encoding="utf-8"))


def init_storage():
    global _STORAGE_READY
    if _STORAGE_READY:
        return

    with DB_LOCK:
        if _STORAGE_READY:
            return
        with connect() as conn:
            queries.create_tables(conn)
            ensure_clean_v2_schema(conn)
            queries.ensure_admins_schema(conn)
            queries.ensure_students_schema(conn)
            queries.ensure_lesson_catalog_schema(conn)
            queries.ensure_subject_summaries_schema(conn)
            queries.ensure_resources_schema(conn)
            queries.ensure_resource_comments_schema(conn)
            queries.ensure_chat_schema(conn)
            queries.ensure_teacher_candidates_schema(conn)
            queries.ensure_teacher_auth_schema(conn)
            queries.ensure_announcements_schema(conn)
            queries.ensure_default_resource_types(conn, utc_now_iso())
            ensure_owner_admin(conn)
            conn.commit()
        _STORAGE_READY = True


def ensure_owner_admin(conn):
    desired_login = OWNER_LOGIN
    if not OWNER_PASSWORD:
        logging.warning(
            "OWNER_ADMIN_PASSWORD is not set; skipping owner admin seeding. "
            "Set it to create or rotate the owner account."
        )
        return
    desired_password_hash = generate_password_hash(OWNER_PASSWORD)

    existing_desired_login = queries.get_admin_id_by_login(conn, desired_login)
    if existing_desired_login:
        target_id = int(existing_desired_login["id"])
        conn.execute(
            """
            UPDATE admins
            SET password_hash = %s, role = 'owner', is_owner = 1
            WHERE id = %s
            """,
            (desired_password_hash, target_id),
        )
        conn.execute(
            """
            UPDATE admins
            SET role = 'admin', is_owner = 0
            WHERE is_owner = 1 AND id != %s
            """,
            (target_id,),
        )
        return

    owner_row = conn.execute(
        """
        SELECT id
        FROM admins
        WHERE is_owner = 1
        ORDER BY id ASC
        LIMIT 1
        """
    ).fetchone()
    if owner_row:
        owner_id = int(owner_row["id"])
        conn.execute(
            """
            UPDATE admins
            SET login = %s, password_hash = %s, role = 'owner', is_owner = 1
            WHERE id = %s
            """,
            (desired_login, desired_password_hash, owner_id),
        )
        conn.execute(
            """
            UPDATE admins
            SET role = 'admin', is_owner = 0
            WHERE is_owner = 1 AND id != %s
            """,
            (owner_id,),
        )
        return

    queries.insert_owner_admin(
        conn,
        desired_login,
        desired_password_hash,
        utc_now_iso(),
    )


__all__ = ["init_storage", "ensure_owner_admin", "ensure_clean_v2_schema"]
