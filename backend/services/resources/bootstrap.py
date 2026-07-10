"""Resource-module startup seeding."""

from backend.core.database import connect_auth_db
from backend.repositories import resources as repository


def seed_default_resource_types(created_at: str) -> None:
    with connect_auth_db() as conn:
        repository.ensure_default_resource_types(conn, created_at)
        conn.commit()


__all__ = ["seed_default_resource_types"]
