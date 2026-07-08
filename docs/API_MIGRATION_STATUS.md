# API Migration Status

Date: 2026-07-08
Branch: `FastAPI-Run-System`

## Phase 0 Inventory

Runtime route inventory:

| Category | Count | Notes |
| --- | ---: | --- |
| `/api/v1/*` JSON routes | 76 | AD/HOD Teacher Academy, admin slices, student chat/comments/office-hours/activity, teacher office hours, auth, system |
| Page/form routes | 57 | Still registered mostly from `backend/roles/*`; includes old admin form mutation URLs under `/admin/*` |
| Static/docs/public routes | 12 | `/`, login/logout, auth handoff, docs, manifest, service worker, unauthorized, static mount |
| Legacy API namespaces | 0 | No runtime routes under `/admin/api`, `/teacher/api`, `/student/api`, `/academic-director/api`, `/head-of-department/api`, or bare non-v1 `/api/*` |
| Total registered routes | 145 | Counted by walking FastAPI included routers recursively |

Remaining legacy API namespace routes:

| Namespace | Runtime routes |
| --- | --- |
| `/admin/api` | none |
| `/teacher/api` | none |
| `/student/api` | none |
| `/academic-director/api` | none |
| `/head-of-department/api` | none |
| bare non-v1 `/api/*` | none |

Legacy import inventory still active:

| Area | Current state |
| --- | --- |
| `backend/api/v1 -> backend.roles.*` | Remaining in AD HOD creation and some admin slices (`staff_registration`, `academic_service`, upload progress helpers) |
| `backend/domains -> backend.roles.*` | Remaining in resources storage helper only after this slice |
| `database.queries` / `database.cross_queries` runtime imports | Still active in identity, communication, office-hours, resources, complaints, parents, demo auth, and some role services |
| `backend.utils.context` runtime imports | Still active in server, identity routes, render helper, and legacy role page/services. Teacher Academy domain permissions no longer import it. |
| `jsonify` | 0 backend Python hits |

Import counts on 2026-07-08:

| Import family | Hits | Files | Main blockers |
| --- | ---: | ---: | --- |
| `database.queries` / `from database import queries` | 13 | 13 | domain services still using query barrel, identity storage/links, demo auth, role services |
| `database.cross_queries` | 1 | 1 | compatibility mention/re-export in student domain queries |
| `backend.utils.context` | 21 | 21 | legacy page routes, server middleware, identity routes, render/session helpers |
| `backend.roles.*` | 63 | 31 | server route registration, page helpers, API v1 admin/AD slices, role services |
| `jsonify` | 0 | 0 | none |

## Role Route File Classification

| File | Classification | Deletion status / blocker |
| --- | --- | --- |
| `backend/roles/academic_director/routes.py` | Page shell route | Blocked until moved to `backend/pages/academic_director.py`; keep URLs including underscore alias until tests prove safe |
| `backend/roles/admin/routes/__init__.py` | Route registry compatibility | Blocked until admin page shell and old form route slices move |
| `backend/roles/admin/routes/academic_routes.py` | JSON/form action route helper | Blocked until remaining old `/admin/academic/*` form posts move to API/page split |
| `backend/roles/admin/routes/admin_page.py` | Mixed page shell + route aggregation | Blocked until `backend/pages/admin.py` exists and admin form mutations move panel-by-panel |
| `backend/roles/admin/routes/admins.py` | Route aggregation compatibility | Blocked by admin resource/student/teacher route modules |
| `backend/roles/admin/routes/resource_routes.py` | Form mutation routes | Blocked until resource mutations move to API v1/domain services |
| `backend/roles/admin/routes/student_routes.py` | Mixed page shell + form mutation routes | Blocked until admin student pages/actions are split |
| `backend/roles/admin/routes/teacher_routes.py` | Form mutation routes | Blocked until admin teacher/candidate panel migration |
| `backend/roles/ceo/routes.py` | Deleted compatibility re-export | Deleted 2026-07-08 after imports from `backend.roles.ceo.routes` reached zero |
| `backend/roles/customer_support/routes.py` | Deleted compatibility re-export | Deleted 2026-07-08 after imports from `backend.roles.customer_support.routes` reached zero |
| `backend/roles/head_of_department/routes.py` | Page shell route | Blocked until moved to `backend/pages/head_of_department.py`; HOD scope wrappers are still local page compatibility |
| `backend/roles/hr_manager/routes.py` | Deleted compatibility re-export | Deleted 2026-07-08 after imports from `backend.roles.hr_manager.routes` reached zero |
| `backend/roles/parent/routes.py` | Mixed page/token route + token form action | Blocked until `backend/pages/parent.py`; preserve invite/link/dashboard behavior |
| `backend/roles/student/routes/__init__.py` | Route registry compatibility | Blocked until student page modules move to `backend/pages/student.py` |
| `backend/roles/student/routes/chat_page.py` | Page shell route | Blocked until student chat page moves to pages layer |
| `backend/roles/student/routes/dashboard.py` | Page shell route | Blocked until dashboard pages move to pages layer |
| `backend/roles/student/routes/office_hours_routes.py` | Page shell route | Blocked until office-hours page moves to pages layer |
| `backend/roles/student/routes/rating_board.py` | Page shell route | Blocked until rating page moves to pages layer |
| `backend/roles/student/routes/resources.py` | Page shell route | Blocked until resources page moves to pages layer |
| `backend/roles/student/routes/student_page.py` | Page shell route + student route registry | Blocked until `backend/pages/student.py` owns page registration |
| `backend/roles/student/routes/students.py` | Legacy form/search/profile actions | Blocked until student public/search/profile actions are split or moved |
| `backend/roles/teacher/routes.py` | Page shell route | Blocked until moved to `backend/pages/teacher.py`; teacher office-hours JSON already lives under API v1 |

## Non-Route Role File Classification

| Area | Classification | Deletion status / blocker |
| --- | --- | --- |
| `backend/roles/*/__init__.py` | Compatibility package exports | Delete only after imports from matching role packages are zero |
| `backend/roles/academic_director/staff_registration.py` | Business service + SQL | Move to domain/identity service before deleting |
| `backend/roles/admin/services/academic_service.py` | Business service + SQL | API v1 admin/AD slices still import it; move by admin academic/student slice |
| `backend/roles/admin/services/insights_service.py` | Business/reporting service | Move to domains/academics or admin reporting service after page split |
| `backend/roles/admin/services/page_service.py` | Page bootstrap service + SQL | Move page bootstrap to domains/pages support after admin page split |
| `backend/roles/admin/services/parent_service.py` | Compatibility service facade | Replace with `domains/parents` imports when import count permits |
| `backend/roles/admin/services/r2_storage_service.py` | Storage integration helper | Domain resources still import it; move to integrations/storage or resources domain |
| `backend/roles/admin/services/route_service.py` | Route/page helper + SQL | Move helper logic to relevant domain services |
| `backend/roles/admin/services/teacher_candidate_service.py` | Business service + SQL/query barrel import | Move to teachers/teacher_academy or HR domain slice |
| `backend/roles/admin/services/upload_progress_service.py` | Upload progress helper | API v1 resources still imports it; move with resources slice |
| `backend/roles/head_of_department/workspace_cards.py` | Page card/bootstrap helper | Move with HOD pages layer |
| `backend/roles/parent/services.py` | Compatibility facade | Replace with domains/parents imports |
| `backend/roles/parent/workspace_cards.py` | Page card/bootstrap helper | Move with parent pages layer |
| `backend/roles/role_home.py` | Shared page render helper | Move to `backend/pages/shared` or keep until all role pages move |
| `backend/roles/student/services/*` | Student page/business compatibility services | Move remaining business logic to domains/students/resources as slices land |
| `backend/roles/teacher/services.py` | Teacher business/page service + SQL | Move to domains/teachers/teacher_academy/timetable |
| `backend/roles/teacher/workspace_cards.py` | Page card/bootstrap helper | Move with teacher pages layer |
| `backend/roles/workspace_counts.py` | Page card/bootstrap helper with SQL | Move to domains/reporting or page bootstrap support |

## Phase 1 Completed

Teacher Academy cleanup:

- Replaced `backend/api/v1/teacher_academy_actions.py` with:
  - `backend/api/v1/teacher_academy/schemas.py`
  - `backend/api/v1/teacher_academy/responses.py`
- Moved HOD Teacher Academy subject-scope logic from `backend/roles/head_of_department/academy_scope.py` to `backend/domains/teacher_academy/permissions.py`.
- Moved Teacher Academy notification helpers from `backend/roles/admin/services/teacher_academy_notifications.py` to `backend/domains/teacher_academy/notifications.py`.
- Moved admin page-cache invalidation backing store into `backend/domains/admin/page_cache.py` and rewired API v1 cache invalidation imports away from `backend.roles.admin.services.page_service`.
- Deleted the obsolete Teacher Academy action, scope, and notification wrapper files after imports were removed.
- Removed remaining session/context coupling from `backend/domains/teacher_academy/permissions.py`; core checks now accept `CurrentUser` or explicit `role/account_id/staff_id`.
- Updated HOD Teacher Academy API routes to pass `CurrentUser` into permission checks and scoped response payloads.
- Tightened `backend/api/v1/teacher_academy/responses.py.__all__` so it exports only response adapters/helpers, not raw domain service functions.

## Phase 2 Completed

Page-shell migration:

- Added `backend/pages/__init__.py`.
- Moved page-only CEO, HR Manager, and Customer Support route bodies into:
  - `backend/pages/ceo.py`
  - `backend/pages/hr_manager.py`
  - `backend/pages/customer_support.py`
- Updated `backend/server.py` to register those page routers from `backend.pages`.
- Deleted `backend/roles/{ceo,hr_manager,customer_support}/routes.py` after import checks showed zero remaining importers.
- Kept `backend/roles/{ceo,hr_manager,customer_support}/__init__.py` as package-level compatibility exports pointing directly to `backend.pages`.

## Migration Map

| Old owner | New owner | Status |
| --- | --- | --- |
| `api/v1/teacher_academy_actions.py` schemas | `api/v1/teacher_academy/schemas.py` | Done |
| `api/v1/teacher_academy_actions.py` response adapters | `api/v1/teacher_academy/responses.py` | Done |
| `roles/head_of_department/academy_scope.py` | `domains/teacher_academy/permissions.py` | Done |
| `roles/admin/services/teacher_academy_notifications.py` | `domains/teacher_academy/notifications.py` | Done |
| `roles/admin/services/page_service.py` cache store | `domains/admin/page_cache.py` | Done |
| CEO/HR/Support page shells | `backend/pages/*` | Done |
| `roles/{ceo,hr_manager,customer_support}/routes.py` compatibility re-exports | deleted; package `__init__.py` exports page registration functions | Done |
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

Most recent full verification for the Phase 2 small-role cleanup:

```bash
python3 -m pytest
npm --prefix frontend run check-types
npm --prefix frontend run build
```

## Next Safe Deletion Candidates

| Candidate | Why next | Blocker |
| --- | --- | --- |
| `backend/roles/head_of_department/routes.py` | Page-only after API v1 Teacher Academy migration | Need `backend/pages/head_of_department.py` and test updates |
| `backend/roles/academic_director/routes.py` | Page-only after API v1 Teacher Academy/HOD actions | Need `backend/pages/academic_director.py`; underscore alias decision |
| `backend/roles/teacher/routes.py` | Page-only; teacher JSON office-hours already migrated | Need `backend/pages/teacher.py`; preserve teacher cabinet bootstrap |

Admin route files are not next deletion candidates. They still contain form mutation routes and should be migrated panel-by-panel.
