# Database Legacy Clarity Report

Branch: FastAPI-Run-System

## Summary

The root `database/` package is still active and must not be deleted in this pass. DB connection ownership moved to `backend.core.database`; `database/database.py` is now only a temporary compatibility wrapper. No database schema, Alembic migration, or Alembic history was changed.

Files deleted from `database/`: none.

## Active Legacy Imports

| Import family | Still imported by | App areas | Later owner |
| --- | --- | --- | --- |
| `database.database` | Direct legacy imports only; app and Alembic now import `backend.core.database` | Compatibility import surface | Delete after direct imports to `database.database` hit zero. |
| `from database import queries` | `backend/identity/*`, `backend/domains/*`, `backend/roles/*`, `backend/utils/demo_auth.py` | Identity bootstrap/auth, resources, announcements, complaints, office hours, payments, academics, role page data, system admin cards | Move one domain at a time into `backend/domains/<domain>/queries.py`; route/page layers should call services. |
| `database.queries.teacher_queries` | Tests and Teacher Academy readiness coverage | Teacher compatibility checks | `backend.domains.teachers.queries`. |
| `database.cross_queries.student_queries` | Tests | Student compatibility checks | `backend.domains.students.queries`. |
| `database.queries.parent_account_queries` and `database.queries.parent_queries` | Tests | Parent compatibility checks | `backend.domains.parents.queries`. |
| `database.queries.announcement_queries` | Tests | Announcement compatibility checks | `backend.domains.announcements.queries`. |
| `database.academics.*` | `backend/utils/session.py`, `backend/utils/demo_auth.py`, `backend/domains/resources`, `backend/domains/payments`, `backend/domains/academics`, `backend/roles/admin/services`, `backend/roles/student/services`, `tgbot/handlers/quick_summary.py` | Canonical school/subject/date/text normalization and academic summaries | Split canonical helpers into `backend/domains/academics` only after all web and Telegram call sites are mapped. |
| `database.tables` | Re-exported from `database/queries/__init__.py` | Legacy query barrel compatibility | Retire after `from database import queries` call sites stop relying on table bootstrap exports. |

## Keep Decisions

| Path | Decision | Why |
| --- | --- | --- |
| `database/alembic/` | KEEP | Owns current migration history. Deleting or moving it would risk Railway/startup migration workflows. |
| `database/database.py` | KEEP_TEMPORARILY | Temporary compatibility wrapper around `backend.core.database`; no longer owns connection implementation. |
| `database/queries/__init__.py` | KEEP_TEMPORARILY | Active `from database import queries` imports remain across backend domains and role services. |
| `database/cross_queries/__init__.py` | KEEP_TEMPORARILY | Shared query re-export remains active while web and Telegram query ownership is split. |
| `database/queries/teacher_queries.py` | KEEP_TEMPORARILY | Re-exports teacher domain queries for compatibility tests and readiness coverage. |
| `database/cross_queries/student_queries.py` | KEEP_TEMPORARILY | Re-exports student domain queries for compatibility tests. |
| `database/queries/parent_account_queries.py` and `database/queries/parent_queries.py` | KEEP_TEMPORARILY | Re-export parent domain queries for compatibility tests. |
| `database/queries/announcement_queries.py` | KEEP_TEMPORARILY | Re-exports announcement domain queries for compatibility tests. |
| `database/queries/complaint_queries.py` | KEEP_REAL_CODE | Still contains support-ticket SQL helpers. Later owner should be `backend/domains/complaints/queries.py`. |
| `database/queries/payment_queries.py` | KEEP_TEMPORARILY | Temporary compatibility wrapper around `backend/domains/payments/queries.py`. |
| `database/queries/resource_queries.py` | KEEP_REAL_CODE | Still contains resource SQL helpers. Later owner should be `backend/domains/resources/queries.py`. |
| `database/queries/office_hours.py` | KEEP_REAL_CODE | Still contains office-hours SQL helpers. Later owner should be `backend/domains/office_hours/queries.py`. |
| `database/queries/lesson_catalog_queries.py` | KEEP_REAL_CODE | Still contains lesson catalog SQL helpers. Later owner should be student/academics domain query modules. |
| `database/queries/subject_summary_queries.py` | KEEP_REAL_CODE | Still contains subject summary SQL helpers. Later owner should be academics domain query modules. |
| `database/queries/admin_queries.py` and `meta_queries.py` | KEEP_REAL_CODE | Still used through the legacy query barrel. Later ownership needs a narrower admin/system domain pass. |
| `database/academics/*` | KEEP_REAL_CODE | Canonical academic helpers and Telegram quick summary still depend on this package. |
| `database/cross_queries/bot_user_queries.py` | KEEP_REAL_CODE | Telegram bot user SQL remains active. |

## Deletable Now

None. `database/database.py` is now only a compatibility wrapper, but keep it until direct legacy imports are proven gone in runtime and operational scripts.

## Later Migration Direction

1. Move payment, complaint, resource, office-hours, lesson catalog, and subject summary SQL into matching `backend/domains/<domain>/queries.py` modules.
2. Replace `from database import queries` in identity/domain/role code with domain services or domain query modules.
3. Keep `database/alembic` stable; its environment now imports `_database_url` from `backend.core.database`.
4. Delete `database/database.py` after direct imports to that module hit zero.
5. Delete legacy query wrappers only after `rg "from database import queries"` and wrapper-specific import checks hit zero.
