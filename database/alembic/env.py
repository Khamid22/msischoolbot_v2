"""Alembic environment for the MSI School app.

Migrations are plain SQL (op.execute) — this project uses raw psycopg queries,
not SQLAlchemy ORM models, so there is no target_metadata / autogenerate.

The database URL comes from the app's own resolver (DATABASE_URL in .env or
Railway), converted to the SQLAlchemy psycopg3 dialect.
"""

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

# Make the app package importable when alembic runs from the repo root.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from backend.core.database import _database_url  # noqa: E402

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _sqlalchemy_url() -> str:
    url = (_database_url() or "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL is not set; cannot run migrations.")
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    # SQLAlchemy 2.0 + psycopg3 dialect (the driver this project already uses).
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


def run_migrations_offline() -> None:
    context.configure(
        url=_sqlalchemy_url(),
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(_sqlalchemy_url(), future=True, pool_pre_ping=True)
    with engine.connect() as connection:
        context.configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
