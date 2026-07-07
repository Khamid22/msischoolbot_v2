# Backend Cleanliness Report

Scope: cleanup/refactor pass on `FastAPI-Run-System`. No database schema changes, no auth behavior changes, no route removals, and no push.

## Old Dependencies Found

| Dependency | Current status | Decision |
| --- | --- | --- |
| `/admin/teacher-academy` | Runtime source no longer registers or posts old Teacher Academy admin action routes. Remaining matches are negative tests and historical docs. | Keep negative tests; no runtime code to delete. |
| `backend.roles.admin.services.teacher_academy_service` / `teacher_academy_service.py` | File is already removed. Tests assert absence. | Keep deletion. |
| `render_admin_page` | Still active for `/admin`, admin subroute form redirects, identity compatibility redirects, and student route compatibility. AD/HOD registration no longer receives it. | KEEP_FOR_NOW. Removing it would break admin/system_admin and compatibility redirects. |
| `admin-home` | Active React page key for the admin workspace only. AD/HOD pages assert they do not render it. | KEEP_FOR_NOW until an admin page-key rename plan exists. |
| `previewRole`, `devPreviewEnabled`, `ADMIN_PREVIEW_ROLES` | Restricted to admin preview behavior and tests. AD/HOD/teacher source guards assert no leakage. | KEEP_FOR_NOW for admin QA, disabled for production unless explicitly enabled. |
| `account_auth_v2` | Old import path is now a compatibility wrapper for clean account auth modules. | KEEP_FOR_NOW until all external imports are gone. |

## Backend Code Changed

- `backend/roles/role_home.py` now accepts a `view` prop and passes it to React.
- `backend/roles/academic_director/routes.py` and `backend/roles/head_of_department/routes.py` pass `view="profile"` only for profile routes.
- `backend/roles/head_of_department/academy_scope.py` no longer embeds HOD Teacher Academy scope SQL or imports `database.queries`; it delegates to domain query helpers and uses `backend.core.database.connect_auth_db`.
- `backend/domains/teacher_academy/queries.py` now owns HOD subject scope SQL and academy teacher/assignment subject lookups.

## Removed Backend Code

No backend files were deleted in this pass. The only backend cleanup was moving SQL ownership from role helper code into the Teacher Academy domain query module.

## Compatibility Code Kept And Why

- `render_admin_page`: required by live admin/system_admin flows and compatibility redirects.
- `admin-home`: active admin React bootstrap key.
- `account_auth_v2.py` and `account_telegram_auth_v2.py`: compatibility wrappers for old imports while login coverage remains green.
- Legacy database wrappers under `database/queries/*`: still imported by active modules and tests until each domain migration is complete.

## Remaining Admin-Centered Dependencies

- Admin route modules still use `render_admin_page` for form responses.
- Identity routes still call `render_admin_page` for compatibility paths.
- Student page registration still receives `render_admin_page` for old dashboard redirects.

These are not AD/HOD dependencies and were left intact to avoid breaking real admin, student, parent, and login flows.

## Next Backend Cleanup Recommendation

1. Create a focused compatibility-render helper so student/identity redirects no longer need the full admin renderer.
2. Continue replacing direct `from database import queries` imports inside one domain at a time.
3. Keep `account_auth_v2` wrappers until source search shows only wrapper tests import them.
4. Do not delete admin preview plumbing until product confirms the admin QA workflow is obsolete.
