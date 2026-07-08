# Database Folder Migration Status

Date: 2026-07-09
Branch: `FastAPI-Run-System`

## Goal

`database/` is being reduced to migration infrastructure only. Runtime connection
ownership belongs in `backend/core/database.py`; runtime SQL belongs in
`backend/domains/*/queries.py`; domain helpers belong under `backend/domains`.

Do not delete `database/alembic/`, drop production data, or rename the physical
`msi_v2` schema during this cleanup.

## Current Import Inventory

| Import family | Hits | Files | Current blocker |
| --- | ---: | ---: | --- |
| `from database import queries` | 12 | 12 | 8 backend runtime imports remain; 4 are architecture test guard strings |
| `database.queries` | 25 | 6 | legacy wrapper tests and compatibility docs/strings remain; runtime callers should migrate off `from database import queries` first |
| `database.cross_queries` | 5 | 3 | student compatibility wrapper tests and compatibility docs/strings remain |
| `database.database` | 0 | 0 | deleted after imports reached zero |
| `database.tables` | 2 | 2 | schema/index ensure helpers still used by payments |
| `database.academics` | 0 | 0 | moved to `backend/domains/academics/*` |

Generated cache cleanup completed:

- Deleted `database/**/__pycache__/`
- Deleted `database/**/*.pyc`

## File Classification

| File | Classification | Current purpose | Target destination | Deletion blocker | Risk | Phase |
| --- | --- | --- | --- | --- | --- | --- |
| `database/__init__.py` | Compatibility package facade | Re-exports core DB helpers and cross queries | delete or migration-only package after imports are gone | `database` package imports still active | Medium | Final database cleanup |
| `database/tables.py` | Schema/table ensure helper | Runtime CREATE/INDEX helpers for `msi_v2` | Alembic migrations or domain setup helpers | `backend/domains/payments/*` imports | Medium | Schema-helper migration |
| `database/alembic/README.md` | Keep migration infrastructure | Alembic docs | keep under `database/alembic` | none | Low | Keep |
| `database/alembic/env.py` | Keep migration infrastructure | Alembic environment | keep under `database/alembic` | migration runtime | Low | Keep |
| `database/alembic/script.py.mako` | Keep migration infrastructure | Alembic revision template | keep under `database/alembic` | migration runtime | Low | Keep |
| `database/alembic/versions/0001_msi_v2_baseline.py` | Keep migration infrastructure | Baseline schema migration | keep under `database/alembic` | migration history | Low | Keep |
| `database/alembic/versions/0001_msi_v2_baseline.sql` | Keep migration infrastructure | Baseline SQL snapshot | keep under `database/alembic` | migration history | Low | Keep |
| `database/alembic/versions/0002_lesson_session_source_metadata.py` | Keep migration infrastructure | Lesson session metadata migration | keep under `database/alembic` | migration history | Low | Keep |
| `database/alembic/versions/0003_shared_accounts_foundation.py` | Keep migration infrastructure | Shared accounts migration | keep under `database/alembic` | migration history | Low | Keep |
| `database/alembic/versions/0004_head_of_department_subject_scopes.py` | Keep migration infrastructure | HOD subject-scope migration | keep under `database/alembic` | migration history | Low | Keep |
| `database/cross_queries/__init__.py` | Legacy shared query barrel | Re-exports cross-query wrappers | remove after importers use domains | query barrel and compatibility tests | Medium | Cross-query cleanup |
| `database/cross_queries/bot_user_queries.py` | Runtime query wrapper | Bot/user lookup SQL compatibility | domain or bot-side query module | importer audit pending | Medium | Cross-query cleanup |
| `database/cross_queries/student_queries.py` | Runtime query wrapper | Student cross-query compatibility | `backend/domains/students/queries.py` | compatibility tests/docs | Medium | Cross-query cleanup |
| `database/queries/__init__.py` | Legacy query barrel | Re-exports remaining old query modules plus DB helpers | delete after callers import domain modules directly | 9 active backend imports still use the query barrel | High | Query barrel cleanup |
| `database/queries/admin_queries.py` | Runtime query wrapper | Admin query compatibility | matching admin/reporting domains | admin services still depend on query barrel | High | Admin panel migration |
| `database/queries/lesson_catalog_queries.py` | Runtime query wrapper | Lesson catalog SQL | `backend/domains/resources` or academics query module | student lesson catalog role service uses query barrel | Medium | Student/resources slice |
| `database/queries/meta_queries.py` | Runtime query wrapper | Metadata/count helper SQL | relevant domains/reporting | query barrel users not split | Medium | Reporting cleanup |
| `database/queries/parent_account_queries.py` | Runtime query wrapper | Parent account SQL | `backend/domains/parents/queries.py` | parent compatibility tests/imports | Medium | Parent slice |
| `database/queries/parent_queries.py` | Runtime query wrapper | Parent portal SQL | `backend/domains/parents/queries.py` | parent compatibility tests/imports | Medium | Parent slice |
| `database/queries/payment_queries.py` | Runtime query wrapper | Payment SQL | `backend/domains/payments/queries.py` | compatibility wrappers/tests | Medium | Payments slice |
| `database/queries/teacher_queries.py` | Runtime query wrapper | Teacher account/profile SQL | `backend/domains/teachers/queries.py` | teacher tests and services still import legacy path | Medium | Teacher slice |

## Completed Slice

Announcement query wrapper cleanup:

- Kept SQL ownership in `backend/domains/announcements/queries.py`.
- Deleted `database/queries/announcement_queries.py`; it was only a re-export compatibility wrapper.
- Removed `from .announcement_queries import *` from `database/queries/__init__.py`.
- Updated tests so active code imports announcement query functions from the domain module.

Student/parent page and small query wrapper cleanup:

- Moved `database/queries/complaint_queries.py` to `backend/domains/complaints/queries.py`.
- Moved `database/queries/office_hours.py` to `backend/domains/office_hours/queries.py`.
- Moved `database/queries/resource_queries.py` to `backend/domains/resources/queries.py`.
- Removed those three re-exports from `database/queries/__init__.py`.
- Updated `backend/domains/complaints/service.py`, `backend/domains/office_hours/service.py`, `backend/domains/resources/service.py`, and `backend/domains/resources/comments_service.py` to import domain query modules directly.
- Updated `backend/identity/storage.py` so default resource types come from `backend.domains.resources.queries`; the file still imports the query barrel for owner admin seeding and remains a later identity cleanup target.

Core DB wrapper and academic helper cleanup:

- Deleted `database/database.py` after `database.database` imports reached zero; runtime connection helpers remain in `backend/core/database.py`.
- Moved academic helper modules from `database/academics/*` into `backend/domains/academics/*`.
- Updated backend and Telegram bot imports to use `backend.domains.academics`.
- Moved subject-summary SQL from `database/queries/subject_summary_queries.py` into `backend/domains/academics/summary_queries.py`.
- Updated `backend/domains/academics/performance_summary.py` to use `backend.core.database.connect_auth_db` and domain summary queries directly.
- Removed the subject-summary re-export from `database/queries/__init__.py`.

## Next Recommended Database Slices

1. Parent query wrappers: migrate only after parent invite/link tests remain green for this page move.
2. Payments: move remaining schema/table helper usage out of `database.tables`.
3. Teacher/lesson catalog query wrappers: migrate with the teacher/student service cleanup slices.
4. Cross-query wrappers: move student/bot identity lookups into `backend/domains/students`, `backend/domains/identity`, or `tgbot`.
5. Admin/reporting query wrappers: migrate panel-by-panel with admin route cleanup.

Do not delete `database/queries/__init__.py` until every `from database import queries`
runtime import is gone.
