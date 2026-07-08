# API Migration Status

Date: 2026-07-08
Branch: `FastAPI-Run-System`

## Phase 0 Inventory

Runtime route inventory:

| Category | Count | Notes |
| --- | ---: | --- |
| `/api/v1/*` JSON routes | 76 | AD/HOD Teacher Academy, admin slices, student chat/comments/office-hours/activity, teacher office hours, auth, system |
| Page/form routes | 62 | Still registered mostly from `backend/roles/*` |
| Static/docs/public routes | 6 | `/static`, OpenAPI docs, manifest, service worker |
| Legacy API namespaces | 0 | No runtime routes under `/admin/api`, `/teacher/api`, `/academic-director/api`, `/head-of-department/api`, or bare non-v1 `/api/*` |

Legacy import inventory still active:

| Area | Current state |
| --- | --- |
| `backend/api/v1 -> backend.roles.*` | Remaining in AD HOD creation and some admin slices (`staff_registration`, `academic_service`, upload progress helpers) |
| `backend/domains -> backend.roles.*` | Remaining in resources storage helper only after this slice |
| `database.queries` / `database.cross_queries` runtime imports | Still active in identity, communication, office-hours, resources, complaints, parents, demo auth, and some role services |
| `backend.utils.context` runtime imports | Still active in server, identity routes, render helper, role routes/services, and domain Teacher Academy permissions for current session scope |

## Phase 1 Completed

Teacher Academy cleanup:

- Replaced `backend/api/v1/teacher_academy_actions.py` with:
  - `backend/api/v1/teacher_academy/schemas.py`
  - `backend/api/v1/teacher_academy/responses.py`
- Moved HOD Teacher Academy subject-scope logic from `backend/roles/head_of_department/academy_scope.py` to `backend/domains/teacher_academy/permissions.py`.
- Moved Teacher Academy notification helpers from `backend/roles/admin/services/teacher_academy_notifications.py` to `backend/domains/teacher_academy/notifications.py`.
- Moved admin page-cache invalidation backing store into `backend/domains/admin/page_cache.py` and rewired API v1 cache invalidation imports away from `backend.roles.admin.services.page_service`.
- Deleted the obsolete Teacher Academy action, scope, and notification wrapper files after imports were removed.

## Phase 2 Started

Page-shell migration:

- Added `backend/pages/__init__.py`.
- Moved page-only CEO, HR Manager, and Customer Support route bodies into:
  - `backend/pages/ceo.py`
  - `backend/pages/hr_manager.py`
  - `backend/pages/customer_support.py`
- Updated `backend/server.py` to register those page routers from `backend.pages`.
- Left `backend/roles/{ceo,hr_manager,customer_support}/routes.py` as compatibility re-exports for existing imports/tests.

## Migration Map

| Old owner | New owner | Status |
| --- | --- | --- |
| `api/v1/teacher_academy_actions.py` schemas | `api/v1/teacher_academy/schemas.py` | Done |
| `api/v1/teacher_academy_actions.py` response adapters | `api/v1/teacher_academy/responses.py` | Done |
| `roles/head_of_department/academy_scope.py` | `domains/teacher_academy/permissions.py` | Done |
| `roles/admin/services/teacher_academy_notifications.py` | `domains/teacher_academy/notifications.py` | Done |
| `roles/admin/services/page_service.py` cache store | `domains/admin/page_cache.py` | Done |
| CEO/HR/Support page shells | `backend/pages/*` | Done |
| Remaining role page shells | `backend/pages/*` | Pending |
| Remaining role business services | matching `backend/domains/*` packages | Pending |
| Remaining database wrappers | matching `backend/domains/*/queries.py` | Pending |

## Verification

Focused backend checks passed:

```bash
python3 -m pytest tests/test_teacher_academy.py tests/test_teacher_academy_clean_api_routes.py tests/test_academic_director_staff_registration.py tests/test_teacher_academy_tomorrow_ready.py tests/test_api_v1_architecture.py tests/test_database_restructure_db2_teachers.py tests/test_database_restructure_db5_academics.py
python3 -m pytest tests/test_architecture_cleanup.py tests/test_phase1d_structure_safety.py tests/test_route_snapshot.py
python3 -m pytest tests/test_role_routing.py tests/test_phase2a_role_workspaces.py tests/test_pages.py tests/test_route_snapshot.py
```

Full-suite and frontend checks remain to run after the next migration slice:

```bash
python3 -m pytest
npm --prefix frontend run check-types
npm --prefix frontend run build
```
