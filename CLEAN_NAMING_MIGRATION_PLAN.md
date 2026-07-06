# Clean Naming Migration Plan

Date: 2026-07-06

## Goal

Remove migration-era naming from the codebase so the LMS reads as if it was designed cleanly from day one, without breaking Railway data, authentication, Teacher Academy, or role login flows.

This document is an audit and migration plan only. Do not rename the live database schema or compatibility columns until the database migration plan below is reviewed, backed up, tested locally, and scheduled for Railway.

## Guardrails

- Do not blindly rename the `msi_v2` database schema.
- Do not break Railway database connections or existing data.
- Do not break password login, Telegram login, parent invite linking, student dashboards, teacher cabinet, or Teacher Academy.
- Do not change database schema without an Alembic migration and rollback plan.
- Keep old import paths as temporary wrappers until all internal references and tests have moved.
- Keep `/admin` available for system/admin compatibility while the core LMS surfaces are separated.

## Search Inventory

Command used:

```bash
rg -n -i "auth_v2|Account Authentication|ACCOUNT_AUTH_V2_ENABLED|account_auth_v2|msi_v2|legacy_source|legacy_login|Phase 1C|Phase 1|\bv2\b|\bold\b|legacy|compatibility|compat" \
  --glob '!backend/static/react/**' \
  --glob '!frontend/node_modules/**' \
  --glob '!node_modules/**' \
  --glob '!*.pyc' \
  --glob '!__pycache__/**'
```

Summary counts from the audit:

| Term | Matches | Files | Classification |
|---|---:|---:|---|
| `auth_v2` | 37 | 8 | REPLACE_THEN_RENAME |
| `Account Authentication` | 26 | 8 | SAFE_RENAME_NOW in docs/UI, REPLACE_THEN_RENAME in code/test names |
| `ACCOUNT_AUTH_V2_ENABLED` | 5 | 2 | SAFE_RENAME_NOW after confirming flag is already removed |
| `account_auth_v2` | 21 | 5 | REPLACE_THEN_RENAME |
| `msi_v2` | 1132 | 69 | DATABASE_MIGRATION_REQUIRED |
| `legacy_source` | 58 | 7 | DATABASE_MIGRATION_REQUIRED |
| `legacy_login` | 11 | 5 | DATABASE_MIGRATION_REQUIRED |
| `Phase 1C` | 5 | 4 | SAFE_RENAME_NOW in docs/tests after auth aliases exist |
| `Phase 1` | 18 | 9 | SAFE_RENAME_NOW when it is planning wording; KEEP_INTERNAL_FOR_NOW in archived migration docs |
| `v2` | 31 | 12 | Mixed: REPLACE_THEN_RENAME for identity modules, DATABASE_MIGRATION_REQUIRED for schema files |
| `old` | 32 | 15 | Mixed: SAFE_RENAME_NOW for comments/docs, KEEP_INTERNAL_FOR_NOW for intentional fallbacks |
| `legacy` | 428 | 51 | Mixed: DATABASE_MIGRATION_REQUIRED for columns, KEEP_INTERNAL_FOR_NOW for compatibility logic |
| `compatibility` | 61 | 21 | KEEP_INTERNAL_FOR_NOW unless it is stale planning text |
| `compat` | 77 | 27 | KEEP_INTERNAL_FOR_NOW unless it is stale planning text |

## Classification

### A. SAFE_RENAME_NOW

These can be cleaned without database changes, as long as the wording change is reviewed and tests stay green.

- Visible/documentation wording:
  - `Account Authentication` -> `Authentication`
  - `Account Authentication` -> `Account Authentication`
  - `MSI v2` -> `LMS`
  - `Training` -> `Teacher Academy` where user-facing
- Stabilization/audit docs:
  - `UI_UX_REPAIR_REPORT.md` references to `Account Authentication`, `legacy`, and `old Admin Console` can be rewritten as clean product language if the report remains useful.
  - Current engineering docs can replace migration-era wording, except archived phase plans that intentionally describe history.
- Test names and comments that do not affect imports:
  - `test_phase1c_*` display names can be renamed once matching import aliases exist.
  - Assertions mentioning `Account Authentication` in failure messages can say `Authentication`.
- Frontend comments and labels:
  - `old hash collided`, `legacy candidate`, `Training teacher`, and similar wording should be cleaned when not referring to a real compatibility path.
- Environment flag references:
  - `ACCOUNT_AUTH_V2_ENABLED` appears only in tests asserting it is absent. After the auth rename lands, replace those checks with the new clean import surface.

### B. REPLACE_THEN_RENAME

These need temporary import wrappers or aliases. Rename them in phases, not in one big move.

- `backend/identity/account_auth_v2.py`
  - Target: `backend/identity/auth.py`
  - Temporary wrapper: keep `account_auth_v2.py` importing/re-exporting from `auth.py`.
- `backend/identity/account_telegram_auth_v2.py`
  - Target: `backend/identity/telegram_auth.py` or `backend/identity/telegram.py`
  - Temporary wrapper: keep `account_telegram_auth_v2.py` importing/re-exporting from the clean module.
- `backend/domains/identity/routes.py`
  - Rename internal helpers:
    - `set_account_auth_v2_session` -> `set_account_session`
    - `account_auth_v2_redirect_url` -> `account_redirect_url`
    - `account_auth_v2_response_role` -> `account_response_role`
    - `record_account_auth_v2_student_activity` -> `record_account_student_activity`
- Tests:
  - `tests/test_phase1c_account_auth_v2.py` -> `tests/test_identity_account_auth.py`
  - `tests/test_phase1c_account_telegram_auth_v2.py` -> `tests/test_identity_telegram_auth.py`
  - `tests/test_phase1c_login_auth_v2.py` -> `tests/test_identity_login.py`
  - `tests/test_phase1c_telegram_auth_v2_routes.py` -> `tests/test_identity_telegram_routes.py`
  - Keep old test behavior; only rename files after imports are stable.
- Teacher Academy provisioning helper:
  - `_provision_teacher_account_v2` -> `_provision_teacher_account`
  - This is a safe code rename, but do it with tests because it sits in Teacher Academy account creation.

### C. DATABASE_MIGRATION_REQUIRED

Do not rename these directly in code until an SQL migration exists and Railway has a rollback path.

- Schema:
  - `msi_v2` -> target `lms`
- Alembic and baseline files:
  - `database/alembic/versions/0001_msi_v2_baseline.py`
  - `database/alembic/versions/0001_msi_v2_baseline.sql`
  - later migrations that refer to `msi_v2`
- Account compatibility columns:
  - `legacy_source_table`
  - `legacy_source_id`
- Teacher profile compatibility column:
  - `legacy_login`
- Student/public identifier compatibility columns:
  - `legacy_student_row_id`
  - `legacy_public_dashboard_id`
  - `legacy_enrollment_id`
- All SQL references in:
  - `backend/domains/academics/*`
  - `backend/domains/announcements/service.py`
  - `backend/domains/complaints/service.py`
  - `backend/identity/*`
  - `backend/roles/*`
  - `database/queries/*`
  - `database/cross_queries/*`
  - `database/tables.py`
  - Alembic migration files

### D. KEEP_INTERNAL_FOR_NOW

These names are still describing real compatibility behavior and should stay until replacement behavior is implemented.

- `/admin` compatibility for system/admin users.
- Session keys that support current redirects and role gates.
- Parent invite linking before Telegram account lookup.
- Student dashboard public id compatibility.
- Backward-compatible fallbacks in student dashboard and lesson catalog services.
- `legacy_*` fields inside database rows until the data model is migrated.
- Archived phase plan documents if the team wants to keep historical context.

## Code Rename Plan

### Phase 1: Add clean identity modules without behavior change

1. Create `backend/identity/auth.py`.
2. Move the implementation from `backend/identity/account_auth_v2.py` into `auth.py`.
3. Keep `backend/identity/account_auth_v2.py` as a compatibility wrapper:

```python
"""Compatibility wrapper for the old account_auth_v2 import path."""

from backend.identity.auth import *  # noqa: F401,F403
```

4. Create `backend/identity/telegram_auth.py`.
5. Move the implementation from `backend/identity/account_telegram_auth_v2.py`.
6. Keep `account_telegram_auth_v2.py` as a wrapper.
7. Add import tests proving both old and new paths work.
8. Do not change behavior, sessions, redirects, roles, or database queries in this phase.

### Phase 2: Update imports gradually

1. Update `backend/domains/identity/routes.py` to import from `backend.identity.auth` and `backend.identity.telegram_auth`.
2. Update tests to import from clean modules.
3. Rename internal helper functions away from `account_auth_v2_*`.
4. Keep wrappers for external/import compatibility.
5. Run the full login and role suites.

### Phase 3: Rename files/tests

1. Rename test files from `phase1c` / `auth_v2` naming to identity-focused names.
2. Update docs from `Account Authentication` to `Authentication`.
3. Add source checks:
   - no `ACCOUNT_AUTH_V2_ENABLED`
   - no `Account Authentication` outside archived migration docs
   - no imports from `backend.identity.account_auth_v2` outside the wrapper test
4. Keep wrapper files until one full deploy cycle has passed.

### Phase 4: Remove compatibility wrappers

Only after:

- Railway has deployed clean imports.
- Logs show no import errors.
- Full test suite passes.
- The team confirms no external scripts import old paths.

Then delete:

- `backend/identity/account_auth_v2.py`
- `backend/identity/account_telegram_auth_v2.py`

## Database Schema Rename Plan

Target: `msi_v2` -> `lms`.

Do not implement this yet.

### Preconditions

1. Full Railway PostgreSQL backup.
2. Local restored copy of Railway data.
3. Alembic migration reviewed.
4. Application code supports configurable schema name or dual-schema lookup during transition.
5. Maintenance window identified.
6. Rollback command tested locally.

### Recommended safe path

1. Add a database schema constant/config:
   - `LMS_DB_SCHEMA=msi_v2` initially.
   - Replace hard-coded SQL with a safe schema helper where practical.
   - Do not use string interpolation for untrusted schema/table names.
2. Add tests that verify all SQL points at the configured schema.
3. Create `lms` schema in local DB.
4. Copy or rename objects from `msi_v2` to `lms`.
5. Validate tables, indexes, constraints, sequences, and grants.
6. Run the application locally against `LMS_DB_SCHEMA=lms`.
7. Run:
   - `python3 -m pytest`
   - `npm --prefix frontend run check-types`
   - `npm --prefix frontend run build`
8. Test all role logins locally against restored data.
9. On Railway:
   - backup
   - apply migration
   - set schema config or search path
   - deploy code
   - run smoke tests
10. Keep `msi_v2` read-only or untouched until verification completes.

### SQL options to evaluate

Option A: `ALTER SCHEMA msi_v2 RENAME TO lms`

- Fastest.
- Highest risk if old code still hard-codes `msi_v2`.
- Requires a deploy where all SQL references have already been changed or schema aliases are supported.

Option B: Create `lms`, copy objects/data, then cut over

- Safer for Railway because `msi_v2` remains intact during verification.
- More work: sequences, indexes, constraints, ownership, grants, triggers, views, and functions must be copied correctly.

Option C: Temporary compatibility views/synonyms

- PostgreSQL has no true schema synonym.
- Could use views in `msi_v2` pointing to `lms` for tables, but writes/defaults/sequences/triggers can become fragile.
- Use only as an emergency bridge, not the preferred long-term design.

### Rollback plan

1. If using `ALTER SCHEMA`, rollback is `ALTER SCHEMA lms RENAME TO msi_v2`, followed by redeploy of old code/config.
2. If using copy/cutover, rollback by switching config/search path back to `msi_v2`.
3. Keep the Railway backup until all smoke tests pass after deploy.
4. Do not drop `msi_v2` in the same deploy as the rename.

## Teacher Academy Domain Rename Plan

Target domain: `backend/domains/teacher_academy`.

Current implementation now lives in the Teacher Academy domain service and
queries. Academic Director and Head of Department routes own the mutation API.
Admin/system admin can still load Teacher Academy rows for compatibility, but
does not own Teacher Academy action routes.

Recommended sequence:

1. Keep `backend/domains/teacher_academy/service.py` as the business logic entrypoint.
2. Keep Teacher Academy SQL in `backend/domains/teacher_academy/queries.py`.
3. Keep old admin action routes removed.
4. Move scope helpers carefully when their domain boundary is clearer:
   - HOD subject guard logic can stay in role layer until domain boundaries are clearer.
5. Rename the shared `adminTeacherAcademy` bootstrap prop with a dual-read fallback.
6. Add tests that Schedule and Assess still submit `assignment_id` / `lesson_assignment_id`.

## UI and Docs Rename Plan

Visible/product-facing renames:

- `Account Authentication` -> `Authentication`
- `Account Authentication` -> `Account Authentication`
- `MSI v2` -> `LMS`
- `Training teacher` -> `Academy teacher`
- `Training lesson` -> `Teacher Academy lesson`
- `Old Admin Console` -> `System Admin workspace` or `/admin compatibility` depending on context

Docs handling:

- Current docs should use clean product names.
- Archived migration plans may keep old names if clearly marked as historical.
- New docs should avoid phase names in filenames unless they are explicitly release/migration records.

## Tests and Checks To Add

Add these after Phase 1 clean identity modules exist:

1. Source checks:
   - no `ACCOUNT_AUTH_V2_ENABLED` references
   - no visible `Account Authentication` label in frontend/docs except archived migration docs
   - no `account_auth_v2` imports except compatibility wrapper tests
   - no user-facing `Training` labels where Teacher Academy is meant
2. Import checks:
   - `backend.identity.auth` exports password authentication APIs
   - `backend.identity.telegram_auth` exports Telegram authentication APIs
   - old import wrappers still work temporarily
3. Login checks:
   - system_admin/admin login
   - Academic Director login
   - HOD login
   - teacher login
   - student login
   - parent login
4. Teacher Academy checks:
   - create Academy Teacher
   - selected lesson count remains correct
   - Schedule still submits `assignment_id`
   - Assess still submits `lesson_assignment_id`
   - HOD subject scope guards still work
5. Database checks before schema rename:
   - application can run against configured schema name in local restored DB
   - no hard-coded `msi_v2` remains in runtime SQL after the schema abstraction phase

## Recommended Rename Order

1. Clean docs/UI wording that has no runtime impact.
2. Add `backend/identity/auth.py` and `backend/identity/telegram_auth.py` with wrappers.
3. Update identity imports and helper names.
4. Rename identity tests away from `phase1c` / `auth_v2`.
5. Move Teacher Academy service into `backend/domains/teacher_academy` with wrapper.
6. Add source checks that prevent migration-era names from returning.
7. Introduce configurable schema support while still pointing to `msi_v2`.
8. Run local restored-DB tests against `lms`.
9. Plan Railway migration window and backup.
10. Rename/cut over database schema.
11. Remove compatibility wrappers and old columns only after one or more successful deploy cycles.

## Immediate Safe Next PR

Recommended first implementation PR:

1. Add `backend/identity/auth.py` and `backend/identity/telegram_auth.py`.
2. Convert old modules into wrappers.
3. Update internal imports in `backend/domains/identity/routes.py`.
4. Rename helper functions in identity routes.
5. Add import compatibility tests.
6. Rename visible docs wording from `Account Authentication` to `Authentication` in current docs.
7. Do not touch `msi_v2`, `legacy_*`, or database migrations.

Required checks for that PR:

```bash
python3 -m pytest
npm --prefix frontend run check-types
npm --prefix frontend run build
git diff --check
```
