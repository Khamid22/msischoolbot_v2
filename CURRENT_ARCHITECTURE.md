# Current Architecture

## Backend Structure

```text
backend/
  server.py                         FastAPI app composition
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
    academic_director/              AD pages and APIs
    head_of_department/             HOD pages and scoped APIs
    admin/                          system/admin workspace
    teacher/                        teacher cabinet
    student/                        student dashboard routes
    parent/                         parent portal routes
  identity/                         temporary compatibility wrappers and shared identity plumbing
  utils/                            request/session/render helpers
```

Role routes should orchestrate requests and permissions. Domain services own business workflows. Domain query modules own SQL for their area.

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
    ui/                             RoleWorkspaceShell, Modal, ActionMenu, MetricCard, tables
    lib/                            routes, bootstrap, Telegram helpers
```

Shared UI components are the preferred place for shells, modals, responsive cards/tables, nav, toasts, badges, and action menus.

## Domains

- Authentication: password and Telegram auth live under `backend/domains/identity` plus clean identity modules. Old account-auth import paths remain wrappers during migration.
- Academics: operational academic queries are in `backend/domains/academics/queries.py`; service modules shape dashboard and admin payloads.
- Timetable: schedule/session SQL lives in `backend/domains/timetable/queries.py`.
- Announcements: CRUD SQL lives in `backend/domains/announcements/queries.py`.
- Teacher Academy: business logic and SQL live in `backend/domains/teacher_academy`.
- Teachers, students, and parents: role-owned queries and services live in their matching domain packages.

## Roles

- `system_admin` / `admin`: admin workspace and operational compatibility.
- `academic_director`: full academic workspace and Teacher Academy management.
- `head_of_department`: subject-scoped academic workspace and Teacher Academy management.
- `teacher`: active teacher or academy teacher cabinet.
- `student`: student dashboard and learning tools.
- `parent`: linked-child parent portal.

## Database Note

The physical PostgreSQL schema is still `msi_v2`. Runtime code may still reference `msi_v2` inside domain query modules and migrations. Do not rename the schema until `SCHEMA_RENAME_MSI_V2_TO_LMS_PLAN.md` is reviewed and scheduled.

Compatibility wrappers remain temporarily in:

- `database/queries/`
- `database/cross_queries/`
- selected `backend/identity/` modules
- selected role service facades

These wrappers should be removed only after import references are eliminated and tests confirm all roles still load.

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
