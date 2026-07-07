# Database Cleanup Report

Date: 2026-07-06

## Scope

Phase 1 database cleanup audit for MSI School LMS / Telegram Mini App.

This phase did not change database schema, Alembic migrations, SQL query behavior, authentication, Teacher Academy, student dashboard, parent flow, Telegram Mini App behavior, or Railway startup logic.

## Current Worktree Warning

Before this Phase 1 audit started, the repository already had unrelated uncommitted changes, including Auth/core/docs/script edits and a pre-existing deletion of `database/rebuild_database_v2.sql`. This report does not validate or explain those unrelated changes. This phase only added this report and removed generated cache clutter.

## Actions Taken

- Inspected the `database/` folder.
- Built an import map for `database`, `database.queries`, `database.cross_queries`, `database.academics`, `database.tables`, `connect_auth_db`, `init_storage`, teacher helper functions, `get_group_gradebook`, and `msi_v2`.
- Classified database files and folders.
- Deleted only generated/cache clutter:
  - `database/__pycache__/`
  - `database/academics/__pycache__/`
  - `database/cross_queries/__pycache__/`
  - `database/queries/__pycache__/`
  - `database/**/*.pyc`
  - `.pytest_cache/`
- Did not delete source files.
- Did not rename the `msi_v2` schema.
- Did not move query modules in this phase.

## Database Tree Summary

Current database tree contains:

- `database/__init__.py`
- `database/database.py`
- `database/tables.py`
- `database/academics/`
- `database/alembic/`
- `database/cross_queries/`
- `database/queries/`

`backend/core/database.py` already exists, but it is currently only a future-facing core import path:

- It exports `connect` from `backend.identity.common`.
- Runtime code still mostly uses `database.connect_auth_db` / `database.queries.connect_auth_db`.
- No new wrapper was created because a core module already exists and changing runtime imports is not required for this audit.

## Import Map

### Active database package entrypoints

- `database.__init__`
  - Re-exports `connect_auth_db`, `get_db_backend`.
  - Imports `database.cross_queries.*`.
- `database.queries`
  - Re-exports `connect_auth_db`, `get_db_backend`.
  - Re-exports `database.cross_queries.*`.
  - Re-exports `database.tables.*`.
  - Re-exports every module under `database/queries`.
- `database.database`
  - Owns active PostgreSQL URL validation, psycopg connection wrapper, bounded pool, and `connect_auth_db`.
- `database.tables`
  - Owns runtime schema ensure helpers still called by active services.

### Active import/reference areas

- `main.py`
  - Uses `init_storage`, which calls database-backed setup.
- `backend/identity/*`
  - Uses `database.queries` for login, password, parent invite, profiles, teacher accounts, Telegram links, and storage setup.
- `backend/domains/*`
  - Uses `database.queries` for resources, announcements, complaints, office hours, payments, academics, and internal dashboards.
- `backend/roles/*`
  - Uses `database.queries`, direct `msi_v2` SQL, and academic normalizers.
- `tgbot/handlers/quick_summary.py`
  - Uses `database.academics.performance_summary`.
- `tests/*`
  - Many tests monkeypatch `database.connect_auth_db` or `database.queries` helpers.

### Important active helper references

- `connect_auth_db`
  - Still central and widely imported via `database` / `database.queries`.
- `init_storage`
  - Called by `main.py`; keep identity storage database setup intact.
- `insert_teacher_auth`
  - Used by teacher account creation and Teacher Academy account provisioning.
- `get_next_teacher_code`
  - Used by Teacher Academy and tests.
- `get_teacher_by_full_name_row`
  - Used by teacher account services and Teacher Academy.
- `get_group_gradebook`
  - Implemented in `backend/roles/admin/services/academic_service.py`, not in `database/queries`.
- `msi_v2`
  - Hard-coded across runtime SQL, Alembic migrations, tests, and docs. This is database-migration work, not a Phase 1 quick rename.

## File Classification

### SAFE_DELETE

Only generated/cache clutter:

- `database/__pycache__/`
- `database/academics/__pycache__/`
- `database/cross_queries/__pycache__/`
- `database/queries/__pycache__/`
- `database/**/*.pyc`
- `.pytest_cache/`

No source file was classified as safe to delete in this phase.

### KEEP_FOR_NOW

These are active and must stay until replacements are implemented and imports are moved.

| Path | Why kept |
|---|---|
| `database/__init__.py` | Public database package entrypoint used by backend/tests. |
| `database/database.py` | Active PostgreSQL connection/pool implementation and `connect_auth_db`. |
| `database/tables.py` | Runtime schema ensure helpers still called by active services. |
| `database/academics/canonical.py` | Re-export surface for school/subject/date/text normalization. |
| `database/academics/dates.py` | Active date parsing/formatting utilities. |
| `database/academics/performance_summary.py` | Used by Telegram quick summary and student/academic summaries. |
| `database/academics/schools.py` | Active school code helpers. |
| `database/academics/subjects.py` | Active subject normalization/sort helpers. |
| `database/academics/text.py` | Active text normalization helper. |
| `database/alembic/README.md` | Migration instructions; do not delete. |
| `database/alembic/env.py` | Alembic runtime; do not delete. |
| `database/alembic/script.py.mako` | Alembic template; do not delete. |
| `database/alembic/versions/0001_msi_v2_baseline.py` | Active baseline migration wrapper. |
| `database/alembic/versions/0001_msi_v2_baseline.sql` | Baseline SQL snapshot currently present; keep pending migration review. |
| `database/alembic/versions/0002_lesson_session_source_metadata.py` | Active migration. |
| `database/alembic/versions/0003_shared_accounts_foundation.py` | Active account/profile migration. |
| `database/alembic/versions/0004_head_of_department_subject_scopes.py` | Active HOD subject-scope migration. |
| `database/cross_queries/__init__.py` | Re-exported by `database.queries`. |
| `database/cross_queries/bot_user_queries.py` | Used by Telegram link helpers. |
| `database/cross_queries/student_queries.py` | Used by student identity/profile/admin flows. |
| `database/queries/__init__.py` | Unified query namespace used broadly. |
| `database/queries/admin_queries.py` | Used by admin/system auth and Telegram links. |
| `database/queries/announcement_queries.py` | Used by announcement domain service. |
| `database/queries/complaint_queries.py` | Used by complaints domain service. |
| `database/queries/lesson_catalog_queries.py` | Used by student lesson catalog service. |
| `database/queries/meta_queries.py` | Metadata helpers; keep until reference audit is deeper. |
| `database/queries/office_hours.py` | Used by office hours domain service. |
| `database/queries/parent_account_queries.py` | Used by parent account and invite flows. |
| `database/queries/parent_queries.py` | Used by parent service. |
| `database/queries/payment_queries.py` | Used by payments domain service. |
| `database/queries/resource_queries.py` | Used by resources domain service and storage defaults. |
| `database/queries/subject_summary_queries.py` | Used by academic performance summaries. |
| `database/queries/teacher_queries.py` | Used by teacher account services and Teacher Academy. |

### REWRITE_NOW

No database source file was rewritten in this phase. The only low-risk cleanup was generated-cache deletion.

Candidates for a future rewrite once tests are in place:

- `database/database.py` -> move connection/pool implementation into `backend/core/database.py`.
- `database/tables.py` -> split runtime ensure helpers by domain or migrate them fully into Alembic/domain setup.
- `database/queries/__init__.py` -> stop broad star re-exports after domain query modules exist.

### REPLACE_THEN_DELETE

These should move to clean architecture, but only after replacements exist and imports are updated.

| Current path | Target replacement |
|---|---|
| `database/database.py` | `backend/core/database.py` |
| `database/tables.py` | Alembic migrations plus domain-specific schema guards only where absolutely needed |
| `database/cross_queries/student_queries.py` | `backend/domains/students/queries.py` and identity-specific query modules |
| `database/cross_queries/bot_user_queries.py` | `backend/identity/telegram_links.py` or `backend/domains/communication/queries.py` |
| `database/queries/admin_queries.py` | `backend/domains/system_admin/queries.py` or `backend/identity/accounts.py` |
| `database/queries/announcement_queries.py` | `backend/domains/announcements/queries.py` |
| `database/queries/complaint_queries.py` | `backend/domains/complaints/queries.py` |
| `database/queries/lesson_catalog_queries.py` | `backend/domains/students/queries.py` or `backend/domains/academics/queries.py` |
| `database/queries/meta_queries.py` | `backend/core/database_meta.py` or domain-owned metadata module |
| `database/queries/office_hours.py` | `backend/domains/timetable/queries.py` or `backend/domains/office_hours/queries.py` |
| `database/queries/parent_account_queries.py` | `backend/domains/parents/queries.py` and `backend/identity/accounts.py` |
| `database/queries/parent_queries.py` | `backend/domains/parents/queries.py` |
| `database/queries/payment_queries.py` | `backend/domains/payments/queries.py` |
| `database/queries/resource_queries.py` | `backend/domains/resources/queries.py` |
| `database/queries/subject_summary_queries.py` | `backend/domains/academics/queries.py` |
| `database/queries/teacher_queries.py` | `backend/domains/teachers/queries.py` and Teacher Academy account helpers |
| `database/academics/performance_summary.py` | `backend/domains/academics/service.py` |
| `database/academics/curriculum.py` | `backend/domains/academics/curriculum.py` or `backend/domains/teacher_academy/queries.py` depending use |

### UNKNOWN

- `database/alembic/versions/0001_msi_v2_baseline.sql`
  - It is currently present in the working tree and referenced by Alembic docs/baseline code, but also appears untracked in current `git status`.
  - Treat as KEEP_FOR_NOW until reviewed against the migration history.
- Pre-existing deletion: `database/rebuild_database_v2.sql`
  - It was already deleted before this Phase 1 work.
  - Do not count it as a Phase 1 deletion.
  - Review separately before committing or restoring.

## Proposed New Database Architecture

Target:

```text
backend/
  core/
    database.py          # connection, pooling, transaction helpers

  domains/
    academics/
      queries.py
      service.py
    teacher_academy/
      queries.py
      service.py
      notifications.py
    timetable/
      queries.py
      service.py
    announcements/
      queries.py
      service.py
    students/
      queries.py
      service.py
    parents/
      queries.py
      service.py
    teachers/
      queries.py
      service.py
```

Keep `database/queries` as compatibility wrappers until all imports are moved.

Recommended sequence:

1. Move connection/pool code from `database/database.py` into `backend/core/database.py`.
2. Keep `database/database.py` as a wrapper:
   - `from backend.core.database import connect_auth_db, get_db_backend`
3. Move domain query modules one at a time.
4. Keep old `database/queries/*.py` modules as wrappers during one deploy cycle.
5. Add source checks that prevent new direct imports from `database.queries`.
6. Remove wrappers only after full test/build and Railway smoke tests pass.

## Domain Query Migration Map

| Current module | Proposed target |
|---|---|
| `database/queries/teacher_queries.py` | `backend/domains/teachers/queries.py`; Teacher Academy-specific helper usage should move into `backend/domains/teacher_academy/queries.py` when appropriate. |
| Teacher Academy SQL | `backend/domains/teacher_academy/queries.py` |
| `database/cross_queries/student_queries.py` | `backend/domains/students/queries.py` plus identity-specific account lookups. |
| `database/queries/parent_account_queries.py` | `backend/domains/parents/queries.py` and `backend/identity/accounts.py`. |
| `database/queries/parent_queries.py` | `backend/domains/parents/queries.py`. |
| `database/queries/announcement_queries.py` | `backend/domains/announcements/queries.py`. |
| `database/queries/office_hours.py` | `backend/domains/timetable/queries.py` or `backend/domains/office_hours/queries.py`. |
| `database/queries/subject_summary_queries.py` | `backend/domains/academics/queries.py`. |
| `database/queries/lesson_catalog_queries.py` | `backend/domains/academics/queries.py` or `backend/domains/students/queries.py`. |
| `database/queries/resource_queries.py` | `backend/domains/resources/queries.py`. |
| `database/queries/payment_queries.py` | `backend/domains/payments/queries.py`. |
| `database/queries/complaint_queries.py` | `backend/domains/complaints/queries.py`. |
| `database/queries/admin_queries.py` | `backend/domains/system_admin/queries.py` or identity account queries. |
| `database/cross_queries/bot_user_queries.py` | `backend/identity/telegram_links.py` query layer or communication queries. |

## Database Schema Rename Plan

Target schema name: `lms`.

Do not implement in Phase 1.

### Preconditions

1. Full Railway PostgreSQL backup.
2. Local restored copy of Railway data.
3. Reviewed Alembic migration.
4. Application can run with configurable schema name or dual-schema compatibility.
5. Maintenance window selected.
6. Rollback tested locally.

### Recommended plan

1. Introduce a safe schema-name abstraction while still defaulting to `msi_v2`.
2. Add source checks and tests to identify remaining hard-coded `msi_v2` runtime SQL.
3. Replace runtime SQL references through a safe schema helper or controlled query builder.
4. Keep Alembic migrations unchanged until the schema rename migration is reviewed.
5. Create `lms` locally from restored data.
6. Validate row counts, sequences, indexes, constraints, permissions, and key workflows.
7. Run full tests/build locally against `lms`.
8. On Railway:
   - take backup
   - apply schema migration or cutover plan
   - set config/search path if needed
   - deploy code
   - run smoke tests
9. Keep `msi_v2` available until verification completes.
10. Do not drop `msi_v2` in the same deploy as the cutover.

### Rollback plan

- If using `ALTER SCHEMA msi_v2 RENAME TO lms`, rollback with `ALTER SCHEMA lms RENAME TO msi_v2` plus redeploy old code/config.
- If using copy/cutover, switch config/search path back to `msi_v2`.
- Restore Railway backup if data mutation occurs.

## Files Deleted In This Phase

Generated/cache clutter only:

- `database/__pycache__/`
- `database/academics/__pycache__/`
- `database/cross_queries/__pycache__/`
- `database/queries/__pycache__/`
- `database/**/*.pyc`
- `.pytest_cache/`

No source files were deleted in this phase.

## Phase 2 Summary

Phase 2 is clear enough to plan, but not safe to start in this turn because it includes aggressive rewrites/deletions and the current worktree is already dirty. Recommended first Phase 2 step:

1. Create `LEGACY_REWRITE_AND_DELETE_REPORT.md`.
2. Inventory legacy/admin/Teacher Academy references.
3. Create `backend/domains/teacher_academy` with wrappers.
4. Add AD/HOD API routes using domain services.
5. Only then reduce old admin dependencies.

No Phase 2 source changes were made.

## Manual Smoke Checklist

| Check | Status |
|---|---|
| AD login | NOT TESTED |
| HOD login | NOT TESTED |
| Teacher login | NOT TESTED |
| Student login | NOT TESTED |
| Parent login | NOT TESTED |
| Teacher Academy open | NOT TESTED |
| Create HOD | NOT TESTED |
| Create Academy Teacher | NOT TESTED |
| Schedule lesson | NOT TESTED |
| Assess lesson | NOT TESTED |
| Telegram Mini App open | NOT TESTED |
| Desktop layout | NOT TESTED |
| Mobile layout | NOT TESTED |
| Railway startup | NOT TESTED |

## Required Verification

- `python3 -m pytest`: passed, 279 tests, 10 warnings.
- `npm --prefix frontend run check-types`: passed.
- `npm --prefix frontend run build`: passed. Vite reported the existing Browserslist stale-data warning.
- `git diff --check`: passed after final whitespace check.
