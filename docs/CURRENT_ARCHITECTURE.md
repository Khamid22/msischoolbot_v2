# Current Architecture

## Backend Structure

```text
backend/
  server.py                         FastAPI app composition
  api/
    v1/
      router.py                     JSON/action API router registry
      academic_director/            AD JSON actions migrated where safe
      head_of_department/           HOD JSON actions migrated where safe
      teacher/                      teacher office-hours API slice
      student/                      student chat/comments/office-hours/activity API slices
      parent/                       placeholder for future safe API migrations
      admin/                        admin API slices for announcements, resources, complaints,
                                    office hours, payments, parents, students, academic, chat
      ceo/                          placeholder for future safe API migrations
      hr_manager/                   placeholder for future safe API migrations
      customer_support/             placeholder for future safe API migrations
  domains/
    academics/                      academic dashboard, programs, groups, enrollments
    announcements/                  announcements query/service layer
    identity/                       login and Telegram authentication routes
    parents/                        parent invites, links, dashboard access
    students/                       student profile, dashboard, account helpers
    teacher_academy/                academy teacher, lesson assignment, schedule, assessment flows,
                                    explicit HOD subject-scope permissions, and notifications
    teachers/                       teacher profiles, auth helpers, subject assignments
    timetable/                      schedule rules and lesson sessions
  roles/
    academic_director/              AD staff-registration compatibility service
    head_of_department/             HOD workspace-card/bootstrap helpers
    admin/                          system/admin workspace
    teacher/                        teacher cabinet bootstrap services
    student/                        student dashboard routes
    parent/                         parent portal routes
  pages/
    academic_director.py            Academic Director page shell
    ceo.py                          CEO page shell
    head_of_department.py           HOD page shell
    hr_manager.py                   HR Manager page shell
    teacher.py                      Teacher page shell
    customer_support.py             Customer Support page shell
  identity/                         temporary compatibility wrappers and shared identity plumbing
  utils/                            request/session/render helpers
```

Role routes should render pages and provide lightweight bootstrap context. API v1 routes should own JSON/action endpoints and permission guards. Domain services own business workflows. Domain query modules own SQL for their area.

## Frontend Structure

```text
frontend/src/
  app/                              React bootstrap and page map
  roles/
    admin/                          system/admin workspace panels
    academic_director/              AD-specific pages
    head_of_department/             HOD-specific pages
    common/                         shared role workspaces
    teacher/                        teacher cabinet
    student/                        student dashboard pages
    parent/                         parent portal
  shared/
    api/                            canonical API route helpers
    ui/                             RoleWorkspaceShell, Modal, ActionMenu, MetricCard, tables
    lib/                            page routes, bootstrap, Telegram helpers
```

Shared UI components are the preferred place for shells, modals, responsive cards/tables, nav, toasts, badges, and action menus.

## Domains

- Authentication: password and Telegram auth live under `backend/domains/identity` plus clean identity modules. Old account-auth import paths remain wrappers during migration.
- Academics: operational academic queries are in `backend/domains/academics/queries.py`; service modules shape dashboard and admin payloads.
- Timetable: schedule/session SQL lives in `backend/domains/timetable/queries.py`.
- Announcements: CRUD SQL lives in `backend/domains/announcements/queries.py`.
- Teacher Academy: business logic and SQL live in `backend/domains/teacher_academy`. Permission helpers accept `CurrentUser` or explicit `role`/`account_id`/`staff_id` values; legacy session lookups stay in page-layer compatibility code.
- Teachers, students, and parents: role-owned queries and services live in their matching domain packages.

## API V1

`backend/api/v1/router.py` is registered by `backend/server.py` before role page routes. The active migrated endpoints are:

- `POST /api/v1/academic-director/head-of-departments`
- `POST /api/v1/academic-director/teacher-academy`
- `POST /api/v1/academic-director/teacher-academy/assignments/{assignment_id}`
- `POST /api/v1/academic-director/teacher-academy/{academy_teacher_id}/assessments`
- `POST /api/v1/academic-director/teacher-academy/{academy_teacher_id}/status`
- `POST /api/v1/academic-director/teacher-academy/{academy_teacher_id}/promote`
- `POST /api/v1/academic-director/teacher-academy/{academy_teacher_id}/delete`
- `POST /api/v1/head-of-department/teacher-academy/assignments/{assignment_id}`
- `POST /api/v1/head-of-department/teacher-academy/{academy_teacher_id}/assessments`
- `POST /api/v1/head-of-department/teacher-academy/{academy_teacher_id}/status`
- admin v1 slices under `/api/v1/admin/*`
- student v1 slices under `/api/v1/student/*`
- teacher office-hours under `/api/v1/teacher/office-hours/*`

`GET /api/v1/auth/me` and `GET /api/v1/system/status` remain in the existing system/auth API modules. Other role API folders exist as placeholders until their current endpoints can move without changing behavior.

Runtime inventory on 2026-07-09: 145 registered routes; 76 are `/api/v1/*`, 57 are page/form routes, and 12 are static/docs/public routes. No runtime route is currently registered under `/admin/api`, `/teacher/api`, `/student/api`, `/academic-director/api`, `/head-of-department/api`, or a bare non-v1 `/api/*` path.

## Roles

- `system_admin` / `admin`: admin workspace and operational compatibility.
- `academic_director`: full academic workspace and Teacher Academy management.
- `head_of_department`: subject-scoped academic workspace and Teacher Academy management.
- `teacher`: active teacher or academy teacher cabinet.
- `student`: student dashboard and learning tools.
- `parent`: linked-child parent portal.
- `academic_director`, `head_of_department`, `teacher`, `ceo`, `hr_manager`, and `customer_support`: page shells now live in `backend/pages/*`; matching `backend/roles/*/routes.py` files have been deleted. The role package `__init__.py` files remain compatibility exports.

## Request Flow Examples

AD creates academy teacher: the frontend submits through `frontend/src/shared/api/routes.ts` to `/api/v1/academic-director/teacher-academy`; the API route uses schemas from `backend/api/v1/teacher_academy/schemas.py` and response adapters from `backend/api/v1/teacher_academy/responses.py`; the helper calls `backend/domains/teacher_academy/service.py`; the service uses `backend/domains/teacher_academy/queries.py`.

HOD schedules or assesses: the frontend submits to `/api/v1/head-of-department/teacher-academy...`; the API route passes `CurrentUser` into `backend/domains/teacher_academy/permissions.py`; the permission helper delegates SQL to `backend/domains/teacher_academy/queries.py`; the shared API response adapter calls the Teacher Academy domain service and filters the returned academy list to the same subject scope.

Teacher sees academy progress: `/teacher` renders from `backend/pages/teacher.py` and receives bootstrap props from temporary role helpers in `backend/roles/teacher/services.py` and `backend/roles/teacher/workspace_cards.py`. Future JSON endpoints should move under `/api/v1/teacher` only after equivalent tests cover the flow.

Student dashboard: `/student` and `/dashboard/{student_id}` currently render from student role routes and domain-backed services. Existing student JSON endpoints remain in their current paths until a no-behavior-change API migration is reviewed.

Parent children dashboard: `/parent` and `/parent/dashboard/{student_row_id}` render from parent role routes backed by the parent/student domains. Parent invite and Telegram linking behavior is unchanged.

## Database Note

The physical PostgreSQL schema is still `msi_v2`. Runtime code may still reference `msi_v2` inside domain query modules and migrations. Do not rename the schema until `SCHEMA_RENAME_MSI_V2_TO_LMS_PLAN.md` is reviewed and scheduled.

Compatibility wrappers remain temporarily in:

- `database/queries/`
- `database/cross_queries/`
- selected `backend/identity/` modules
- selected role service facades

These wrappers should be removed only after import references are eliminated and tests confirm all roles still load.
`docs/DATABASE_FOLDER_MIGRATION_STATUS.md` tracks file-by-file database cleanup. `database/queries/announcement_queries.py` has been deleted because announcement SQL is owned by `backend/domains/announcements/queries.py`.

## Legacy Remaining

- `database/` remains because Alembic history, compatibility query wrappers, and active imports still depend on it.
- The physical schema remains `msi_v2`; the `lms` rename is only planned.
- Many old page and form routes still live in `backend/roles/`, including `/admin/*` form actions plus student and parent route modules. AD, HOD, teacher, CEO, HR Manager, and Customer Support page shells have moved to `backend/pages`, and their old role `routes.py` files are deleted.
- Admin page routes still use `render_admin_page` because the system/admin workspace has not been moved to `backend/pages/admin.py` yet.
- API v1 still has temporary imports from role services for a few admin/AD slices (`staff_registration`, `academic_service`, upload progress/storage helpers). These are tracked for later domain moves.

## Local Run

```bash
pip install -r requirements.txt
python main.py
```

Frontend checks:

```bash
npm --prefix frontend run check-types
npm --prefix frontend run build
```

Backend checks:

```bash
python3 -m pytest
```

## Railway Deployment Notes

- Set `DATABASE_URL`, `BOT_TOKEN`, `MINI_APP_URL`, and `APP_SECRET_KEY`.
- Keep the current database schema as `msi_v2` until the schema rename is reviewed.
- Run migrations only through reviewed Alembic/database scripts.
- Build frontend before deploy if generated React assets are expected in the deployment artifact.
- Never test destructive database cleanup directly on Railway production.

## Smoke Checklist

| Area | Check |
| --- | --- |
| Auth | system/admin, Academic Director, HOD, teacher, student, and parent login work. |
| Academic Director | Overview, Teacher Academy, HOD management, timetable, announcements, and profile/logout load. |
| HOD | Overview, Teacher Academy, timetable, announcements, and profile/logout load with subject scope. |
| Teacher Academy | Create teacher, selected lesson count, Schedule, Assess, Review/Promote flows work. |
| Teacher | Academy and active teacher cabinets work on desktop and mobile. |
| Student | Dashboard opens, subject dashboards resolve, no parent/admin data leaks. |
| Parent | Invite link, Telegram linking, linked child dashboard, and parent portal work. |
| Responsive | Desktop, laptop, tablet, phone, and Telegram Mini App layouts remain usable. |
| Data safety | No password hashes in props; no schema rename; no dummy data invented. |
