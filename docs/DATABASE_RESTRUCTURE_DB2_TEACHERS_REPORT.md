# Database Restructure DB-2 Teachers Report

Date: 2026-07-07

Scope: Move teacher-owned query and service access into the teacher domain without changing the physical database schema. The database schema remains `msi_v2`.

No database schema changes were made. Student and parent query modules were not moved in this phase.

## Created / Updated

| Path | Purpose |
| --- | --- |
| `backend/domains/teachers/queries.py` | New teacher domain SQL helper module. Owns teacher rows, auth helpers, profile helpers, and subject/group assignment helpers. |
| `backend/domains/teachers/service.py` | New teacher domain service facade. Owns list/get/create/update/delete teacher behavior and teacher login provisioning helpers. |
| `backend/domains/teachers/__init__.py` | Teacher domain package marker. |
| `database/queries/teacher_queries.py` | Temporary compatibility wrapper re-exporting `backend.domains.teachers.queries`. |
| `backend/identity/teachers.py` | Temporary compatibility wrapper re-exporting `backend.domains.teachers.service`. |
| `tests/test_database_restructure_db2_teachers.py` | DB-2 source/import contract coverage. |

## Moved Query Functions

Moved from `database/queries/teacher_queries.py` to `backend/domains/teachers/queries.py`:

- `list_teachers_rows`
- `get_teacher_login_row`
- `get_teacher_by_telegram_id`
- `get_teacher_auth_row_by_id`
- `list_teacher_ids_without_auth`
- `get_next_teacher_code`
- `get_next_teacher_login`
- `insert_teacher_auth`
- `update_teacher_password`
- `get_teacher_by_id_row`
- `insert_teacher_row`
- `insert_teacher_profile_row`
- `upsert_teacher_subject`
- `set_teacher_group_assignment`
- `activate_teacher_profile`
- `get_teacher_by_group_row`
- `get_teacher_by_full_name_row`
- `delete_teacher_by_group`
- `update_teacher_row_by_id`
- `delete_teacher_row_by_id`

## Moved Service Functions

Moved from `backend/identity/teachers.py` to `backend/domains/teachers/service.py`:

- `backfill_teacher_auth`
- `subject_teacher_login_prefix`
- `normalize_teacher_category`
- `normalize_teacher_semester_stage`
- `coerce_teacher_performance_score`
- `coerce_supervised_lessons`
- `teacher_payload`
- `list_teachers`
- `get_teacher_by_id`
- `upsert_teacher`
- `update_teacher_by_id`
- `delete_teacher_by_id`
- `get_teacher_name_by_group`
- `assign_teacher_to_group`

## Imports Updated Where Safe

- `backend/roles/teacher/services.py` now imports teacher helpers from `backend.domains.teachers.service`.
- `backend/domains/teacher_academy/service.py` now imports `list_teachers` and `upsert_teacher` from `backend.domains.teachers.service`.
- `backend/domains/teacher_academy/queries.py` now uses `backend.domains.teachers.queries` for teacher helper query exports.
- `backend/api/v1/teacher_academy_actions.py` imports `list_teachers` from `backend.domains.teachers.service`.
- `backend/roles/common/teacher_academy_api.py` now re-exports the API v1 Teacher Academy helpers as a temporary compatibility wrapper.
- `backend/roles/admin/routes/teacher_routes.py` now imports teacher CRUD helpers from `backend.domains.teachers.service`.
- `backend/roles/admin/services/page_service.py` now imports `list_teachers` from `backend.domains.teachers.service`.

## Wrappers Kept

| Wrapper | Why kept |
| --- | --- |
| `database/queries/teacher_queries.py` | Keeps old query imports working while remaining callers and tests migrate. |
| `backend/identity/teachers.py` | Keeps `backend.identity.account_service` and older identity imports working temporarily. |
| `backend/identity/account_service.py` | Still re-exports teacher helpers for legacy identity/student/admin edges. |

## Remaining Legacy Teacher References

| Reference | Reason |
| --- | --- |
| `backend/identity/account_service.py` -> `backend.identity.teachers` | Compatibility aggregate still needed by existing identity, student, and admin code. |
| `backend/identity/profiles.py` -> `backend.identity.teachers.get_teacher_name_by_group` | Left for compatibility; parent/student profile flow was intentionally not touched in DB-2. |
| `backend/roles/student/*` imports from `backend.identity.account_service` | Student flow intentionally untouched this phase. |
| `backend/domains/identity/*` imports from `backend.identity.account_service` | Login/auth compatibility boundary left intact. |
| Tests importing `database.queries.teacher_queries` or `backend.identity.teachers` | Intentional coverage that wrappers still work. |

## Verification

Focused verification:

```bash
python3 -m pytest tests/test_database_restructure_db2_teachers.py tests/test_database_restructure_db1.py tests/test_teacher_accounts.py
```

Result: passed, `13 passed`.

Full verification:

```bash
python3 -m pytest
npm --prefix frontend run check-types
npm --prefix frontend run build
git diff --check
```

Results:

- `python3 -m pytest`: passed, `316 passed, 11 warnings`.
- `npm --prefix frontend run check-types`: passed.
- `npm --prefix frontend run build`: passed.
- `git diff --check`: passed.
