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
      teacher/                      placeholder for future safe API migrations
      student/                      placeholder for future safe API migrations
      parent/                       placeholder for future safe API migrations
      admin/                        placeholder; active admin APIs remain in /admin/api
      ceo/                          placeholder for future safe API migrations
      hr_manager/                   placeholder for future safe API migrations
      customer_support/             placeholder for future safe API migrations
  domains/
    academics/                      academic dashboard, programs, groups, enrollments
    announcements/                  announcements query/service layer
    identity/                       login and Telegram authentication routes
    parents/                        parent invites, links, dashboard access
    students/                       student profile, dashboard, account helpers
    teacher_academy/                academy teacher, lesson assignment, schedule, assessment flows
    teachers/                       teacher profiles, auth helpers, subject assignments
    timetable/                      schedule rules and lesson sessions
  roles/
    academic_director/              AD page rendering and bootstrap context
    head_of_department/             HOD page rendering and bootstrap context
    admin/                          system/admin workspace
    teacher/                        teacher cabinet
    student/                        student dashboard routes
    parent/                         parent portal routes
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
- Teacher Academy: business logic and SQL live in `backend/domains/teacher_academy`.
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

`GET /api/v1/auth/me` and `GET /api/v1/system/status` remain in the existing system/auth API modules. Other role API folders exist as placeholders until their current endpoints can move without changing behavior.

## Roles

- `system_admin` / `admin`: admin workspace and operational compatibility.
- `academic_director`: full academic workspace and Teacher Academy management.
- `head_of_department`: subject-scoped academic workspace and Teacher Academy management.
- `teacher`: active teacher or academy teacher cabinet.
- `student`: student dashboard and learning tools.
- `parent`: linked-child parent portal.

## Request Flow Examples

AD creates academy teacher: the frontend submits through `frontend/src/shared/api/routes.ts` to `/api/v1/academic-director/teacher-academy`; the API route calls `backend/api/v1/teacher_academy_actions.py`; the helper calls `backend/domains/teacher_academy/service.py`; the service uses `backend/domains/teacher_academy/queries.py`.

HOD schedules or assesses: the frontend submits to `/api/v1/head-of-department/teacher-academy...`; the API route checks HOD subject scope through `backend/roles/head_of_department/academy_scope.py`; the scope helper delegates SQL to `backend/domains/teacher_academy/queries.py`; the shared API action helper calls the Teacher Academy domain service.

Teacher sees academy progress: `/teacher` renders the teacher cabinet page and receives bootstrap props from `backend/roles/teacher/routes.py` and `backend/roles/teacher/services.py`. Future JSON endpoints should move under `/api/v1/teacher` only after equivalent tests cover the flow.

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

## Legacy Remaining

- `database/` remains because Alembic history, compatibility query wrappers, and active imports still depend on it.
- The physical schema remains `msi_v2`; the `lms` rename is only planned.
- `/admin/api`, `/teacher/api`, and several student/general `/api` endpoints remain active until equivalent `/api/v1` replacements are implemented and tested.
- `backend/roles/common/teacher_academy_api.py` remains as a compatibility wrapper around `backend/api/v1/teacher_academy_actions.py`.
- Admin page routes still use `render_admin_page` because the system/admin workspace has not been moved to an API/page split yet.

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
