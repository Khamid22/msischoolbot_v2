# Teacher Academy Legacy Deletion Record

Status: completed

## Removed Old Admin Dependency

Removed old admin Teacher Academy action routes. Teacher Academy mutations now
belong to the Academic Director and Head of Department role APIs.

Removed `backend/roles/admin/services/teacher_academy_service.py`.

Removed `adminTeacherAcademy...` frontend action helpers from `frontend/src/shared/lib/routes.ts`.

## Canonical Teacher Academy Paths

The canonical implementation lives in:

- `backend/domains/teacher_academy/service.py`
- `backend/domains/teacher_academy/queries.py`
- `backend/roles/common/teacher_academy_api.py`

Academic Director mode uses `/academic-director/api/teacher-academy...`.

Head of Department mode uses `/head-of-department/api/teacher-academy...`.

Admin/system admin no longer posts Teacher Academy actions through `/admin`.

## Remaining Admin Usage

Admin page context may still read Teacher Academy rows for display through
`backend.domains.teacher_academy.service.list_academy_teachers`.

The shared frontend prop name `adminTeacherAcademy` remains as a page bootstrap
data field for now. It is not an action route and does not post to `/admin`.

## Regression Checks

Tests should keep proving:

- AD create/schedule/assess/status/promote/delete routes are registered.
- HOD schedule/assess/status routes are registered and subject-scoped.
- Old admin Teacher Academy action routes are not registered.
- `routes.adminTeacherAcademy...` helpers are absent.
- The old admin service wrapper file is absent.
- Admin/system admin Teacher Academy view is read-only for actions that now
  belong to Academic Director and Head of Department.
