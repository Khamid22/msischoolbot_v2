"""msi_v2 baseline schema

Baseline snapshot of the clean msi_v2 schema. On a fresh database this creates
the entire schema; on the existing local/prod databases (already at this shape)
it is idempotent (CREATE ... IF NOT EXISTS / ADD COLUMN IF NOT EXISTS) — or the
database is simply stamped at this revision.

Future schema changes are new migrations, not edits to rebuild_database_v2.sql.

Revision ID: 0001_msi_v2_baseline
Revises:
Create Date: 2026-07-01
"""
from pathlib import Path

from alembic import op

# revision identifiers, used by Alembic.
revision = "0001_msi_v2_baseline"
down_revision = None
branch_labels = None
depends_on = None

_SCHEMA_SQL = Path(__file__).resolve().parents[2] / "scripts" / "rebuild_database_v2.sql"


def _schema_sql() -> str:
    raw = _SCHEMA_SQL.read_text(encoding="utf-8")
    # Alembic wraps each migration in its own transaction; drop the file's own
    # BEGIN;/COMMIT; so they don't clash with it.
    kept = [
        line
        for line in raw.splitlines()
        if line.strip().upper().rstrip(";") not in {"BEGIN", "COMMIT"}
    ]
    return "\n".join(kept)


def upgrade() -> None:
    op.execute(_schema_sql())


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS msi_v2 CASCADE")
