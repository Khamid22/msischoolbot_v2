# Database Folder Migration Status

Date: 2026-07-10

Branch documented: `FastAPI-Run-System`

## Result

The database-folder runtime cleanup is complete. Runtime connection ownership is `backend/core/database.py`, runtime SQL is owned by domain query modules, and schema DDL is owned by Alembic.

Current source files under `database/` are limited to:

```text
database/__init__.py              narrow re-export of core connection helpers
database/alembic/env.py           Alembic environment
database/alembic/script.py.mako   revision template
database/alembic/README.md        migration instructions
database/alembic/versions/*       frozen baseline and revisions through 0007
```

Generated `__pycache__` files are not architecture and must not be committed.

## Deleted Runtime Surfaces

- `database/database.py`
- `database/tables.py`
- `database/academics/*`
- `database/queries/*`
- `database/cross_queries/*`

Their responsibilities moved to:

- connection/pool: `backend/core/database.py`;
- academic canonical helpers/services/queries: `backend/domains/academics`;
- identity SQL: `backend/domains/identity/queries.py`;
- role/domain SQL: matching `backend/domains/*/queries.py` modules;
- table/index/constraint creation: Alembic migrations.

## Migration Inventory

| Revision | State |
| --- | --- |
| `0001_msi_v2_baseline` | retained frozen baseline |
| `0002_lesson_source_meta` | retained |
| `0003_shared_accounts` | retained |
| `0004_hod_subject_scopes` | retained |
| `0005_canonical_identity` | canonical account/password cutover |
| `0006_secure_parent_invites` | hash-only single-use parent invites |
| `0007_lms_integrity` | identity and academic/office-hour constraints |

## Enforcement

Architecture tests should keep these invariants true:

- backend/tgbot code has no imports from `database.queries`, `database.cross_queries`, or `database.tables`;
- runtime Python contains no request-time schema/table/index creation;
- migrations are the only DDL owner;
- domain services import focused domain query modules rather than a global barrel.

Useful audit commands:

```bash
rg "database\\.(queries|cross_queries|tables)|from database import queries" backend tgbot main.py
rg "CREATE TABLE|CREATE INDEX|ALTER TABLE" backend tgbot main.py
python3 -m pytest tests/test_architecture_cleanup.py tests/test_phase1d_structure_safety.py
```

No physical schema rename was performed. `msi_v2` remains intentionally active.
