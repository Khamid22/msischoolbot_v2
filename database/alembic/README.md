# Database migrations (Alembic)

The `msi_v2` schema is owned by Alembic. `scripts/rebuild_database_v2.sql` is the
frozen **baseline snapshot** (migration `0001_msi_v2_baseline`); do **not** edit it
for new changes — add a migration instead.

The DB URL is read from `DATABASE_URL` (`.env` locally, injected on Railway) by
`alembic/env.py`. Migrations are plain SQL via `op.execute(...)` (this project
uses raw psycopg, not the SQLAlchemy ORM).

## Everyday commands (run from the repo root)

```bash
# where is the DB now / what's the latest?
python -m alembic current
python -m alembic heads

# apply all pending migrations (also runs automatically on Railway deploy)
python -m alembic upgrade head

# create a new migration, then edit its upgrade()/downgrade() with op.execute(SQL)
python -m alembic revision -m "add X to Y"

# undo the last migration
python -m alembic downgrade -1
```

## Setting up a fresh database
```bash
python -m alembic upgrade head    # builds the whole msi_v2 schema
python main.py web                # seeds owner + default resource types on startup
```

## Notes
- Deploys apply migrations in `scripts/railway_start.sh` (`alembic upgrade head`)
  before the app starts; a failed migration aborts the deploy (no downtime).
- To point at production, set `DATABASE_URL` to the Railway **public** URL for the
  command, e.g. `DATABASE_URL="postgresql://…proxy.rlwy.net:PORT/railway" python -m alembic current`.
