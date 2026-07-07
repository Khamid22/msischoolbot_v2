# Database Restructure Phase DB-1 Report

## 1. Current Database Import Map

DB-1 keeps the physical PostgreSQL schema unchanged and leaves the old database package in place.

- `backend.core.database` is now the owner of connection helpers. `database.database` is only a temporary compatibility wrapper.
- `backend.domains.teacher_academy.service` owns Teacher Academy business logic and imports `backend.domains.teacher_academy.queries`.
- `backend.domains.teacher_academy.queries` owns Teacher Academy SQL while still using the existing `msi_v2` schema and compatibility helpers from `database.queries`.
- Academic Director, HOD, and Teacher Cabinet role edges now import safe Teacher Academy functions from `backend.domains.teacher_academy.service`.
- Admin/system admin can still read Teacher Academy rows through page context, but old admin Teacher Academy mutation routes and the admin service wrapper are removed.

## 2. New Modules Created

- `backend/domains/teacher_academy/__init__.py`
- `backend/domains/teacher_academy/queries.py`
- `backend/domains/teacher_academy/service.py`
- `tests/test_database_restructure_db1.py`
- `DATABASE_RESTRUCTURE_PHASE_DB1_REPORT.md`

## 3. Query Functions Moved

Teacher Academy SQL moved out of the service layer into `backend.domains.teacher_academy.queries`:

- `get_subject_program`
- `list_curriculum_lessons`
- `list_active_subjects`
- `list_active_group_options`
- `list_curriculum_programs`
- `list_curriculum_items`
- `list_academy_teacher_rows`
- `get_academy_teacher_row_for_account`
- `list_assignment_rows`
- `list_assessment_rows`
- `list_academy_teacher_account_backfill_rows`
- `update_academy_teacher_user_id`
- `get_teacher_name`
- `phase1_accounts_available`
- `get_teacher_account_for_provisioning`
- `update_teacher_account_for_provisioning`
- `insert_teacher_account_for_provisioning`
- `get_teacher_profile_for_provisioning`
- `update_teacher_profile_for_provisioning`
- `insert_teacher_profile_for_provisioning`
- `insert_academy_teacher`
- `insert_academy_lesson_assignment`
- `get_assignment_schedule_row`
- `update_assignment_schedule`
- `get_assignment_for_assessment`
- `insert_assessment`
- `update_assignment_status`
- `get_academy_teacher_id`
- `update_academy_teacher_status`
- `touch_academy_teacher`
- `approve_academy_teacher_promotion`

The following legacy Teacher Academy helpers remain re-exported from `database.queries` for compatibility during DB-1:

- `ensure_teacher_academy_schema`
- `get_teacher_by_full_name_row`
- `insert_teacher_profile_row`
- `upsert_teacher_subject`
- `get_teacher_auth_row_by_id`
- `get_next_teacher_code`
- `insert_teacher_auth`
- `activate_teacher_profile`
- `set_teacher_group_assignment`

## 4. Compatibility Kept

- `database/database.py`, `database/queries`, `database/cross_queries`, and `database/tables.py` remain untouched.
- Admin/system admin page compatibility remains, but Teacher Academy mutations use AD/HOD role APIs.

## 5. Old Database Modules Still Used

Intentionally retained for DB-1:

- `database/database.py`
- `database/tables.py`
- `database/queries/__init__.py`
- `database/queries/*`
- `database/cross_queries/*`
- `database/academics/*`
- `database/alembic/*`

These modules are still used by identity services, admin services, student/parent flows, announcements, resources, academics, payments, office hours, and Railway/Alembic startup.

## 6. Remaining Direct Database Imports

Remaining `from database import queries` or old database imports are outside the DB-1 Teacher Academy slice and should be handled in later phases:

- `backend/identity/common.py`
- `backend/identity/profiles.py`
- `backend/identity/teachers.py`
- `backend/identity/passwords.py`
- `backend/identity/telegram_links.py`
- `backend/identity/parent_accounts.py`
- `backend/identity/parent_invites.py`
- `backend/identity/student_accounts.py`
- `backend/identity/storage.py`
- `backend/utils/demo_auth.py`
- `backend/domains/academics/postgres_service.py`
- `backend/domains/academics/internal_dashboard_service.py`
- `backend/domains/announcements/service.py`
- `backend/domains/communication/chat_service.py`
- `backend/domains/complaints/service.py`
- `backend/domains/office_hours/service.py`
- `backend/domains/payments/service.py`
- `backend/domains/resources/service.py`
- `backend/roles/academic_director/staff_registration.py`
- `backend/roles/admin/routes/chat_admin_routes.py`
- `backend/roles/admin/services/academic_service.py`
- `backend/roles/admin/services/page_service.py`
- `backend/roles/admin/services/parent_service.py`
- `backend/roles/admin/services/route_service.py`
- `backend/roles/admin/services/teacher_candidate_service.py`
- `backend/roles/admin/system_admin_cards.py`
- `backend/roles/head_of_department/academy_scope.py`
- `backend/roles/parent/services.py`
- `backend/roles/student/routes/chat_routes.py`
- `backend/roles/student/routes/comment_routes.py`
- `backend/roles/student/services/lesson_catalog_service.py`
- `backend/roles/teacher/services.py`
- `database/academics/performance_summary.py`
- `database/alembic/env.py`

## 7. Recommended DB-2 Phase

Recommended next slice:

1. Create `backend/domains/academics/queries.py` for timetable, schedules, sessions, groups, attendance, homework, exams, and gradebook reads/writes.
2. Move `backend/roles/admin/services/academic_service.py` SQL into the academics query module.
3. Keep `academic_service.py` as business logic only.
4. Add compatibility exports only after tests prove admin, Academic Director, HOD, student, and teacher pages still load.
5. Do not rename `msi_v2` or change Alembic until a separate physical schema migration plan is approved.

## 8. Risks Found

- The Teacher Academy admin service had many direct SQL calls mixed with business rules; DB-1 separated those but kept behavior intact.
- The old Teacher Academy admin service path is no longer used by admin teacher routes.
- `msi_v2` references remain in the new Teacher Academy query module by design. Renaming the physical schema requires a separate Railway-safe migration plan.
- HOD scope, staff registration, announcements, academics, student, parent, and teacher support services still contain direct SQL and old database imports. Those are out of DB-1 scope.
- `datetime.utcnow()` warnings still exist in existing helper code; DB-1 did not change time behavior.

## 9. Test Results

- `python3 -m pytest`: passed, `284 passed, 10 warnings`
- `npm --prefix frontend run check-types`: passed
- `npm --prefix frontend run build`: passed
- `git diff --check`: passed

No backend schema, Alembic migration, Auth, Railway config, student dashboard, parent flow, or teacher cabinet logic was changed.
