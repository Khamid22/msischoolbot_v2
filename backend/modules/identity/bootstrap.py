"""Identity storage bootstrap and owner seeding."""

import logging
import os

from backend.core.passwords import generate_password_hash
from backend.modules.academics.resources.bootstrap import seed_default_resource_types
from backend.modules.identity.service import synchronize_staff_account
from backend.modules.identity import repository as identity_repository

from backend.modules.identity.database import DB_LOCK, connect, utc_now_iso

OWNER_LOGIN = (os.environ.get("OWNER_ADMIN_LOGIN", "admin") or "admin").strip()
OWNER_PASSWORD = (os.environ.get("OWNER_ADMIN_PASSWORD", "") or "").strip()

_STORAGE_READY = False


def init_storage():
    global _STORAGE_READY
    if _STORAGE_READY:
        return

    with DB_LOCK:
        if _STORAGE_READY:
            return
        # The msi_v2 schema is owned by Alembic migrations (applied on deploy via
        # `alembic upgrade head`; run it manually for local dev). Startup only
        # seeds identity data. Resource-module seeding uses its own boundary.
        seed_default_resource_types(utc_now_iso())
        with connect() as conn:
            ensure_owner_admin(conn)
            conn.commit()
        _STORAGE_READY = True


def ensure_owner_admin(conn):
    desired_login = OWNER_LOGIN
    if not OWNER_PASSWORD:
        logging.warning(
            "OWNER_ADMIN_PASSWORD is not set; skipping owner admin seeding. "
            "Set it before the first deployment to create the owner account."
        )
        return
    existing_desired_login = identity_repository.get_staff_by_login(conn, desired_login)
    target_id = 0
    if existing_desired_login:
        target_id = int(existing_desired_login["id"])
        identity_repository.promote_staff_owner(conn, target_id)
        identity_repository.demote_other_staff_owners(conn, target_id)
    else:
        owner_row = identity_repository.get_first_owner_staff(conn)
        if owner_row:
            target_id = int(owner_row["id"])
            identity_repository.rename_owner_staff(
                conn, staff_id=target_id, login=desired_login
            )
        else:
            initial_hash = generate_password_hash(OWNER_PASSWORD)
            inserted = identity_repository.insert_owner_staff(
                conn, login=desired_login, password_hash=initial_hash
            )
            target_id = int(inserted["id"] or 0) if inserted else 0

    if target_id <= 0:
        raise RuntimeError("Unable to seed the owner staff identity.")
    identity_repository.demote_other_staff_owners(conn, target_id)
    existing_account = identity_repository.find_staff_account_row(
        conn,
        staff_id=target_id,
        login=desired_login,
    )
    existing_account = dict(existing_account) if existing_account else None
    canonical_hash = str(existing_account.get("password_hash") or "").strip() if existing_account else ""
    canonical_must_change = bool(existing_account.get("must_change_password")) if existing_account else OWNER_PASSWORD == desired_login
    if not canonical_hash:
        canonical_hash = generate_password_hash(OWNER_PASSWORD)

    account_id = synchronize_staff_account(
        conn,
        staff_id=target_id,
        login=desired_login,
        password_hash=canonical_hash,
        role="system_admin",
        full_name="MSI Portal Owner",
        job_title="Owner",
        department="System",
        must_change_password=canonical_must_change,
    )
    if account_id <= 0:
        raise RuntimeError("Unable to seed the canonical owner account.")


__all__ = ["init_storage", "ensure_owner_admin"]
