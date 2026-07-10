# Database Migrations

Alembic is the only owner of PostgreSQL schema DDL. Runtime services must not create tables, indexes, or constraints.

The physical schema remains `msi_v2`. `versions/0001_msi_v2_baseline.sql` is the frozen baseline snapshot for `0001_msi_v2_baseline`; never edit it for a new change.

## Current Revision Chain

```text
0001_msi_v2_baseline
  -> 0002_lesson_source_meta
  -> 0003_shared_accounts
  -> 0004_hod_subject_scopes
  -> 0005_canonical_identity
  -> 0006_secure_parent_invites
  -> 0007_lms_integrity
```

Important migration properties:

- `0005` makes `accounts` the sole password authority and removes legacy student credential storage.
- `0006` hashes existing invite values, deletes plaintext invite storage, and is intentionally irreversible.
- `0007` adds identity, invite, office-hour, enrollment, grade, attendance, and coin integrity constraints.

## Commands

Run from the repository root:

```bash
python -m alembic current
python -m alembic heads
python -m alembic upgrade head
python -m alembic revision -m "describe change"
python -m alembic downgrade -1
```

`DATABASE_URL` is read by `database/alembic/env.py`. Railway applies `python -m alembic upgrade head` in `scripts/railway_start.sh` before starting the application.

## Verification Rules

- Test upgrades on a disposable database or clone containing representative pre-migration data.
- Back up before destructive or irreversible migrations.
- Verify `current` equals `heads` after upgrade.
- Run backend tests and application smoke checks after migration.
- Do not run a downgrade for `0006`; restore a pre-`0006` backup or regenerate invites.
- Never point ad hoc local verification commands at production.
