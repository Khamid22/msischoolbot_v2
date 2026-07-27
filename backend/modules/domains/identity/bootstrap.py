"""Runtime data bootstrap for non-DDL module defaults."""

from backend.modules.domains.academics.resources.bootstrap import seed_default_resource_types

from backend.modules.domains.identity.database import DB_LOCK, utc_now_iso

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
        # seeds module defaults. Resource-module seeding uses its own boundary.
        seed_default_resource_types(utc_now_iso())
        _STORAGE_READY = True


__all__ = ["init_storage"]
