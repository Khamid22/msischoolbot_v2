# Database Architecture Cleanup Report

Scope: safe database-access cleanup only. The physical schema remains `msi_v2`; no migrations or Alembic files were changed.

## Database Imports Found

Broad source search still finds old database imports in these groups:

| Group | Examples | Status |
| --- | --- | --- |
| Teacher-related | `database/queries/teacher_queries.py`, `backend/roles/teacher/services.py` | Partially migrated; wrappers still active. |
| Student-related | `database/cross_queries/student_queries.py`, student services/routes | Partially migrated; wrappers still active. |
| Parent-related | `database/queries/parent_queries.py`, `parent_account_queries.py` | Partially migrated; wrappers still active. |
| Academic dashboard | `backend/domains/academics/*`, `backend/roles/admin/services/academic_service.py` | Domain query migration started; admin service still uses old facade. |
| Timetable | `backend/domains/timetable/queries.py` | Domain query module exists and owns schedule/session SQL. |
| Announcements | `backend/domains/announcements/queries.py` | Domain query module exists; old query wrapper kept. |
| Auth/account | `backend/identity/*`, `backend/core/database.py` | Keep until auth/account migration is complete. |
| Infrastructure | `database/alembic/env.py`, `database/queries/__init__.py`, `database/tables.py` | Still needed for migrations and compatibility facade. |

## Functions Moved In This Pass

HOD Teacher Academy subject-scope SQL moved into `backend/domains/teacher_academy/queries.py`:

- `list_hod_subject_scope_rows`
- `get_academy_teacher_subject_id`
- `get_assignment_subject_id`

`backend/roles/head_of_department/academy_scope.py` now delegates to those helpers and no longer embeds `msi_v2` SQL.

## Wrappers Kept

- `database/queries/teacher_queries.py`
- `database/cross_queries/student_queries.py`
- `database/queries/parent_queries.py`
- `database/queries/parent_account_queries.py`
- `database/queries/announcement_queries.py`

They remain intentionally because active imports and compatibility tests still rely on them.

## Old Database Modules Still Required

- `database.database`: wrapped by `backend/core/database.py` and used by Alembic.
- `database.queries`: compatibility facade for active admin/student/identity modules.
- `database.academics.canonical`: canonical normalization helpers still used across backend code.
- `database.tables`: table bootstrap helpers for still-active flows.

## Remaining Database Cleanup Phases

1. Move resource/payment/complaint/chat query groups into domain query modules.
2. Move admin academic service reads/writes behind `backend/domains/academics` service/query APIs.
3. Move identity/account query access behind identity domain modules.
4. Remove each old wrapper only after source search shows no runtime imports and tests cover the replacement.
5. Plan `msi_v2 -> lms` physical schema rename separately, with backup/rollback.

## Risk Notes

- Directly deleting `database.queries` or `database.database` is high risk today.
- Directly renaming `msi_v2` would break Railway unless done with a migration window and rollback.
- Moving all remaining database imports at once would be too large for review.
