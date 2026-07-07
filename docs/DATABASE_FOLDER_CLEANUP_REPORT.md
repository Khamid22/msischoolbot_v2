# Database Folder Cleanup Report

Date: 2026-07-07

Scope: audit and documentation for the root `database/` folder during API v1 cleanup. No database schema was changed and no Alembic history was moved.

## Import Audit Summary

| Import group | Status | Reason |
| --- | --- | --- |
| `database.database` | KEEP_TEMPORARILY | Temporary compatibility wrapper around `backend/core/database.py`. |
| `database.queries` | KEEP | Active wrappers remain for teachers, students, parents, announcements, and admin compatibility. |
| `database.cross_queries` | KEEP | Student/parent dashboard compatibility still depends on these modules. |
| `database.academics` | KEEP | Canonical academic helpers remain active. |
| `database.tables` | KEEP | Table bootstrap/metadata helpers are still referenced. |
| `database/alembic` | KEEP | Alembic history stays in place until the migration-folder move is separately planned and reviewed. |

## Deleted Files Or Folders

None in this pass.

## Moved Functions

No new root-database file moves were made in this pass. Existing domain query migrations remain active from earlier DB phases, and HOD Teacher Academy scope SQL now belongs to `backend/domains/teacher_academy/queries.py`.

## Alembic Location Decision

Alembic remains under `database/alembic`. Moving it to `migrations/alembic` would require path/config updates and deployment rehearsal, so it was not done in this cleanup pass.

## Remaining Database Imports

Remaining imports are intentional until each domain replacement is proven and covered by tests. The next safe targets are teacher office-hours, student dashboard/resources/chat, parent dashboard/linking, and admin academic APIs.
