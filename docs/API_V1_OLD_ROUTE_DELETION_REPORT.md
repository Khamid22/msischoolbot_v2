# API V1 Old Route Deletion Report

Date: 2026-07-07

Scope: safe JSON/action route migration only. No database schema, auth behavior, Railway config, Telegram linking, role page URLs, or business rules were changed.

## API V1 Layer Created

- `backend/api/__init__.py` keeps the existing API schema/response exports.
- `backend/api/v1/__init__.py` identifies the API v1 package.
- `backend/api/v1/router.py` registers role API routers under `/api/v1`.
- Empty role API folders were created for future safe migrations: `teacher`, `student`, `parent`, `admin`, `ceo`, `hr_manager`, and `customer_support`.

## New Active API V1 Routes

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/v1/academic-director/head-of-departments` | Create HOD account from AD workspace |
| POST | `/api/v1/academic-director/teacher-academy` | Create Academy Teacher |
| POST | `/api/v1/academic-director/teacher-academy/assignments/{assignment_id}` | Schedule/update academy assignment |
| POST | `/api/v1/academic-director/teacher-academy/{academy_teacher_id}/assessments` | Save academy assessment |
| POST | `/api/v1/academic-director/teacher-academy/{academy_teacher_id}/status` | Update academy status |
| POST | `/api/v1/academic-director/teacher-academy/{academy_teacher_id}/promote` | Promote academy teacher |
| POST | `/api/v1/academic-director/teacher-academy/{academy_teacher_id}/delete` | Delete academy teacher |
| POST | `/api/v1/head-of-department/teacher-academy/assignments/{assignment_id}` | HOD schedule/update scoped assignment |
| POST | `/api/v1/head-of-department/teacher-academy/{academy_teacher_id}/assessments` | HOD save scoped assessment |
| POST | `/api/v1/head-of-department/teacher-academy/{academy_teacher_id}/status` | HOD update scoped academy status |

## Old Routes Deleted

Removed active route registrations for:

- `/academic-director/api/head-of-departments`
- `/academic-director/api/teacher-academy...`
- `/head-of-department/api/teacher-academy...`

Tests now assert those role-local action routes are absent while the role page URLs remain.

## Old Routes Kept

- `/admin/api/...`: kept because the active admin/system-admin UI still uses it.
- `/teacher/api/office-hours/...`: kept because the teacher cabinet still uses it.
- Student/general `/api/...`: kept because the student dashboard, resources, chat, and office-hours flows still depend on them.

## Frontend URLs Updated

`frontend/src/shared/api/routes.ts` now owns the canonical AD/HOD Teacher Academy action URLs. `frontend/src/shared/lib/routes.ts` reuses those helpers so existing component imports keep working.

## Tests Covering New Routes

- `tests/test_api_v1_architecture.py`
- `tests/test_teacher_academy_clean_api_routes.py`
- `tests/test_academic_director_staff_registration.py`
- `tests/test_teacher_academy_tomorrow_ready.py`
- `tests/test_route_snapshot.py`
