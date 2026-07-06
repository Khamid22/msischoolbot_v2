# Database Restructure DB-3 Students Report

Date: 2026-07-07

Scope: Move student-owned query and service access into the student domain without changing the physical database schema. The database schema remains `msi_v2`.

No database schema changes were made. Parent and teacher domains were not moved in this phase, except for replacing student-dashboard mapping calls at parent/admin edges.

## Created / Updated

| Path | Purpose |
| --- | --- |
| `backend/domains/students/queries.py` | New student domain SQL helper module. Owns student login/profile rows, dashboard-id mapping, student subject enrollments, admin rows, password rows, Telegram student rows, and public dashboard target lookup. |
| `backend/domains/students/service.py` | New student domain service facade. Owns student admin listing, activity tracking, profile lookup, dashboard profile lookup, password changes, subject switch enrollments, office-hour subject options, and public dashboard resolution. |
| `backend/domains/students/__init__.py` | Student domain package marker. |
| `database/cross_queries/student_queries.py` | Temporary compatibility wrapper re-exporting `backend.domains.students.queries`. |
| `backend/identity/student_accounts.py` | Temporary compatibility wrapper re-exporting student account helpers from `backend.domains.students.service`. |
| `backend/identity/profiles.py` | Temporary compatibility wrapper re-exporting student profile helpers from `backend.domains.students.service`. |
| `backend/identity/passwords.py` | Temporary compatibility wrapper re-exporting student password helpers from `backend.domains.students.service`. |
| `tests/test_database_restructure_db3_students.py` | DB-3 source/import contract coverage. |

## Moved Query Functions

Moved from `database/cross_queries/student_queries.py` to `backend/domains/students/queries.py`:

- `get_student_login_row`
- `get_next_student_code`
- `get_students_sheet_map_row`
- `update_student_last_seen`
- `list_students_for_admin_rows`
- `get_student_admin_row`
- `get_student_auth_row_by_id`
- `update_student_password`
- `update_student_admin_profile`
- `get_student_conflict_by_telegram_id`
- `clear_student_telegram_user_conflicts`
- `update_student_telegram_user`
- `get_student_by_telegram_id`

Added student-domain query helpers for logic that was previously inline near role pages:

- `list_online_only_student_rows`
- `get_active_enrollment_for_student_row`
- `list_active_student_enrollments`
- `list_classmate_names`
- `get_student_ref_by_public_dashboard_id`
- `get_student_ref_by_public_dashboard_id_and_school`
- `list_subject_enrollment_rows_for_student`
- `list_active_subject_options_for_student`
- `list_public_dashboard_targets_for_student_row`

## Moved Service Functions

Moved into `backend/domains/students/service.py`:

- `record_student_activity`
- `list_students_for_admin`
- `update_student_admin_profile`
- `split_name`
- `extract_auto_student_context`
- `get_admin_student_profile`
- `get_dashboard_student_profile`
- `get_student_db_id_by_enrollment_id`
- `get_student_subject_enrollments`
- `list_enrolled_subject_options`
- `change_student_password`
- `admin_change_student_password`
- `school_code_from_name`
- `resolve_public_dashboard_for_student_row`
- `resolve_sheet_student_for_admin`

## Imports Updated Where Safe

- `backend/roles/student/services/dashboard_service.py` now imports profile/dashboard helpers from `backend.domains.students.service`.
- `backend/roles/student/routes/student_page.py` now imports activity and dashboard-id helpers from `backend.domains.students.service`.
- `backend/roles/student/routes/students.py` now imports `change_student_password` from `backend.domains.students.service`.
- `backend/roles/student/routes/office_hours_routes.py` now uses `list_enrolled_subject_options` from `backend.domains.students.service` and `list_teachers` from `backend.domains.teachers.service`.
- `backend/roles/admin/routes/student_routes.py` now imports student CRUD/profile/password helpers from `backend.domains.students.service`.
- `backend/roles/admin/services/page_service.py` now imports student admin/profile helpers from `backend.domains.students.service`.
- `backend/roles/admin/services/route_service.py` now re-exports `resolve_sheet_student_for_admin` from the student domain instead of owning dashboard lookup SQL.
- `backend/roles/parent/services.py` now resolves child dashboard targets through `backend.domains.students.service`.
- `backend/domains/academics/internal_dashboard_service.py` keeps `get_student_subject_enrollments` as a compatibility wrapper around the student-domain service.

## Wrappers Kept

| Wrapper | Why kept |
| --- | --- |
| `database/cross_queries/student_queries.py` | Keeps old cross-query imports working while callers migrate. |
| `backend/identity/student_accounts.py` | Keeps `backend.identity.account_service` and older imports working temporarily. |
| `backend/identity/profiles.py` | Keeps old profile imports working temporarily. |
| `backend/identity/passwords.py` | Keeps old password imports working temporarily. |
| `backend/domains/academics/internal_dashboard_service.get_student_subject_enrollments` | Keeps older dashboard subject-switch imports working while new role code uses the student domain. |
| `backend/identity/account_service.py` | Still re-exports student helpers for legacy identity/auth edges. |

## Remaining Legacy Student References

| Reference | Reason |
| --- | --- |
| `backend/domains/identity/*` imports from `backend.identity.account_service` | Login/auth compatibility boundary left intact. |
| `backend/identity/telegram_links.py` uses `database.queries` aggregate | Mixed-role Telegram linking remains in identity for now; student query calls continue to work through the compatibility wrapper. |
| `backend/identity/account_auth.py` has student login SQL | Authentication was explicitly out of scope for DB-3. |
| `database/queries/parent_account_queries.py`, `database/queries/parent_queries.py` | Parent query phase is separate; parent flow was only updated to call student-domain dashboard resolution. |
| `backend/domains/academics/internal_dashboard_service.py` | Still owns academic dashboard payload assembly and attendance/homework payloads; only student subject enrollment switching was wrapped into the student domain in this phase. |
| `backend/roles/student/services/lesson_catalog_service.py` | Lesson catalog remains a student-route service, but not a moved database/cross-query student helper in DB-3. |

## Verification

Focused verification:

```bash
python3 -m pytest tests/test_database_restructure_db3_students.py tests/test_student_dashboard_service.py tests/test_phase2a_student_dashboard_safety.py tests/test_phase2a_parent_workspace_cards.py
```

Result: passed, `43 passed, 4 warnings`.

Full verification:

```bash
python3 -m pytest
npm --prefix frontend run check-types
npm --prefix frontend run build
git diff --check
```

Results:

- `python3 -m pytest`: passed, `322 passed, 11 warnings`.
- `npm --prefix frontend run check-types`: passed.
- `npm --prefix frontend run build`: passed.
- `git diff --check`: passed.
