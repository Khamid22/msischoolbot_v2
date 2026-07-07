# Domain Query Migration Report

Date: 2026-07-07

Scope: safe query/domain movement only. No schema, migration, or data changes were made.

## Functions Moved Or Reused

HOD Teacher Academy subject-scope SQL is now in `backend/domains/teacher_academy/queries.py`:

- `list_hod_subject_scope_rows`
- `get_academy_teacher_subject_id`
- `get_assignment_subject_id`

`backend/roles/head_of_department/academy_scope.py` delegates to those query helpers and keeps the subject-scope policy wrapper for active HOD routes and API v1.

## Domain Modules Used

- `backend/domains/teacher_academy/service.py`
- `backend/domains/teacher_academy/queries.py`
- `backend/domains/teachers/service.py`
- Existing domains for students, parents, academics, timetable, announcements, and identity remain as established by earlier DB restructuring phases.

## Wrappers Kept

- `backend/roles/common/teacher_academy_api.py`: re-exports `backend/api/v1/teacher_academy_actions.py` for compatibility.
- `database/queries/*`: kept where active imports remain.
- `database/cross_queries/*`: kept where student/parent/admin compatibility still imports it.
- selected role service facades: kept where active role routes still import them.

## Imports Updated

- AD/HOD action routes now import API v1 helpers instead of role-common implementations.
- Tests now monkeypatch `backend.api.v1.teacher_academy_actions` and `backend.api.v1.head_of_department.router` for migrated behavior.
- `tests/test_database_restructure_db2_teachers.py` follows the moved Teacher Academy API helper path.

## Remaining Database Imports

Remaining database imports are documented in `docs/DATABASE_FOLDER_CLEANUP_REPORT.md` and are kept until their callers move behind domain service/query modules.

## Risks

- Moving all admin/student/teacher query groups in one pass would risk unrelated role regressions.
- `backend/api/v1/academic_director/router.py` still imports HOD account creation from `backend.roles.academic_director.staff_registration`; this is documented for a future identity/staff domain move because changing it now would touch account creation behavior.
