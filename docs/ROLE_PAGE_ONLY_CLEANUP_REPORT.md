# Role Page-Only Cleanup Report

Date: 2026-07-07

Scope: role route cleanup where safe. No role page URL was changed.

## Role Files Cleaned

| Role file | Status |
| --- | --- |
| `backend/roles/academic_director/routes.py` | Page-only after moving HOD creation and Teacher Academy POST actions to `/api/v1/academic-director`. |
| `backend/roles/head_of_department/routes.py` | Page-only after moving scoped Teacher Academy POST actions to `/api/v1/head-of-department`. |

Both files now retain GET page routes, `render_react_page`, CSRF/bootstrap context, and role workspace metadata.

## Remaining Non-Page Logic

| Area | Why kept |
| --- | --- |
| `backend/roles/admin/routes/*` | Active system/admin workspace still owns `/admin`, `/admin/api`, admin form posts, and `render_admin_page`. Moving it safely needs a dedicated admin API phase. |
| `backend/roles/teacher/routes.py` | Teacher office-hours JSON endpoints remain active under `/teacher/api`. They were not moved because the task forbids breaking teacher cabinet behavior. |
| `backend/roles/student/routes/*` | Student dashboard, chat, resources, comments, metadata, and office-hours endpoints remain active. Moving them needs student/parent regression coverage first. |
| `backend/roles/parent/routes.py` | Parent invite/link/dashboard behavior remains unchanged to protect parent flow and Telegram linking. |

## render_admin_page References

`render_admin_page` remains only in admin/student compatibility paths where active admin or embedded admin/student views still depend on it. It is not used by the new `/api/v1` package and is not used by AD/HOD Teacher Academy action routes.

## Next Cleanup Needed

1. Move teacher office-hours JSON endpoints to `/api/v1/teacher`.
2. Move student dashboard/resource/chat JSON endpoints to `/api/v1/student`.
3. Move parent child/dashboard JSON helpers to `/api/v1/parent`.
4. Move admin APIs only after the admin UI is updated to consume `/api/v1/admin`.
