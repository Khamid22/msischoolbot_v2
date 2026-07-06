# Schema Rename Plan: `msi_v2` to `lms`

## Status

Planning only. Do not implement until reviewed, backed up, tested locally, and scheduled for a Railway maintenance window.

## Goal

Move the physical PostgreSQL schema name from `msi_v2` to `lms` after runtime query ownership is clean and all schema references are known.

## Preconditions

- All runtime SQL is isolated in domain query modules or migration files.
- Full test suite passes against a local restored production-like database.
- Railway production database has a fresh backup.
- A rollback build is ready.
- No deploy or data import job is running during the migration window.

## Backup

1. Create a Railway database backup/snapshot.
2. Export a logical dump:

```bash
pg_dump "$DATABASE_URL" --format=custom --file=backup-before-msi-v2-to-lms.dump
```

3. Record current migration revision and app commit SHA.
4. Verify backup restore locally before touching production.

## Local Restore Drill

1. Create an empty local database.
2. Restore the dump:

```bash
pg_restore --dbname "$LOCAL_DATABASE_URL" --clean --if-exists backup-before-msi-v2-to-lms.dump
```

3. Run the migration plan locally.
4. Run:

```bash
python3 -m pytest
npm --prefix frontend run check-types
npm --prefix frontend run build
```

5. Smoke test all roles locally.

## Migration SQL Options

### Option A: Direct Schema Rename

```sql
BEGIN;
ALTER SCHEMA msi_v2 RENAME TO lms;
COMMIT;
```

Pros:

- Fast and simple.
- Preserves objects, sequences, indexes, and constraints.

Cons:

- Any hardcoded `msi_v2` runtime query fails immediately.
- Rollback requires another schema rename and matching app redeploy.

### Option B: Copy/Cutover

1. Create `lms` schema.
2. Copy tables, sequences, defaults, indexes, constraints, and privileges.
3. Run app against `lms`.
4. Keep `msi_v2` untouched until verification is complete.

Pros:

- Safer rollback because `msi_v2` remains intact.

Cons:

- More complex and slower.
- Requires careful sequence/default ownership checks.

### Option C: Search Path Transition

1. Introduce an application schema setting, for example `LMS_DB_SCHEMA`.
2. Keep default as `msi_v2`.
3. Update query modules to use a reviewed schema abstraction or `search_path`.
4. Deploy with `LMS_DB_SCHEMA=msi_v2`.
5. Rename/copy schema.
6. Switch to `LMS_DB_SCHEMA=lms`.

Pros:

- Allows staged deploy.
- Reduces risk from hardcoded names.

Cons:

- Requires disciplined query abstraction and tests.

## Recommended Strategy

Use Option C first, then choose direct rename or copy/cutover after hardcoded runtime references are eliminated.

## Code Query Update Strategy

1. Inventory all `msi_v2` references:

```bash
rg -n "msi_v2" backend database tests docs
```

2. Classify references:

- Runtime query module
- Alembic migration
- Test fixture/assertion
- Documentation
- Historical archive

3. Add a schema-name abstraction only in runtime query modules.
4. Keep migrations explicit and historical.
5. Add source tests preventing new hardcoded runtime references outside approved query modules during transition.
6. Run full tests against both schema names locally if using copy/cutover.

## Railway Migration Window

1. Announce maintenance window.
2. Stop background jobs/imports.
3. Confirm no active deploy is running.
4. Take Railway snapshot and logical dump.
5. Deploy code that can target both schemas, still pointing to `msi_v2`.
6. Run migration locally one final time.
7. Apply production migration.
8. Switch runtime schema setting if using Option C.
9. Restart Railway service.
10. Run smoke checklist immediately.

## Rollback Plan

Direct rename rollback:

```sql
BEGIN;
ALTER SCHEMA lms RENAME TO msi_v2;
COMMIT;
```

Then redeploy the previous app commit/config.

Copy/cutover rollback:

1. Switch runtime schema setting back to `msi_v2`.
2. Redeploy previous app commit if needed.
3. Keep `lms` untouched for forensic comparison.

Snapshot rollback:

1. Restore Railway snapshot only if schema rollback is not enough.
2. Treat this as a data-loss-risk operation and confirm with stakeholders first.

## Test Plan

- `python3 -m pytest`
- `npm --prefix frontend run check-types`
- `npm --prefix frontend run build`
- `git diff --check`
- Login smoke test for system/admin, Academic Director, HOD, teacher, student, and parent.
- Academic Director pages: Overview, Teacher Academy, HOD, Timetable, Announcements, Profile.
- HOD pages: Overview, Teacher Academy, Timetable, Announcements, Profile with subject scope.
- Teacher Academy: create teacher, schedule lesson, assess lesson, promote/review.
- Teacher cabinet: academy and active teacher modes.
- Student dashboard and parent linked-child dashboard.
- Telegram Mini App parent invite/link flow.

## Do Not Do

- Do not drop `msi_v2` in the same deploy.
- Do not run destructive cleanup before the app is verified on `lms`.
- Do not hide schema failures with broad exception fallbacks.
- Do not migrate Railway without a tested rollback.
