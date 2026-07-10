# Engineering Module Map

Audience: engineers locating the current owner of a change.

## Repository Map

```text
backend/
  api/v1/                         versioned JSON/action routes
  pages/                          role and dashboard page bootstraps
  domains/                        business services and domain SQL
  core/                           config and PostgreSQL connection
  integrations/                   Telegram, Excel, storage adapters
  security/                       CurrentUser, roles, permissions
  identity/                       shared startup/connection plumbing only
  roles/                          remaining admin/workspace compatibility helpers
  server.py                       app and middleware composition

database/
  __init__.py                     narrow core-connection compatibility export
  alembic/                        all schema DDL and migration history

frontend/src/
  app/                            bootstrap and lazy page registry
  roles/                          role-owned pages/panels
  shared/api/                     route definitions
  shared/lib/                     time, metrics, motion, Telegram, bootstrap
  shared/ui/                      accessible/responsive UI primitives

tgbot/
  routing.py                      explicit empty inbound router registry
  keyboards/                      retained keyboard primitives
  settings.py                     bot settings

scripts/
  railway_start.sh                migrate then start deployment process
  reconcile_academic_workbooks.py explicit workbook reconciliation entrypoint
```

## Change Routing

| Change | Primary owner |
| --- | --- |
| account/password/session | `backend/domains/identity`, `backend/api/v1/auth`, `backend/security` |
| Telegram Mini App verification | `backend/integrations/telegram` |
| parent invite/link/access | `backend/domains/parents`, `backend/pages/parent.py` |
| schools/groups/programs/gradebook | `backend/domains/academics` |
| schedules/lesson sessions | `backend/domains/timetable` |
| office-hour rules | `backend/domains/office_hours` |
| students | `backend/domains/students` |
| teachers | `backend/domains/teachers` |
| Teacher Academy | `backend/domains/teacher_academy` |
| payments | `backend/domains/payments` |
| chat | `backend/domains/communication` |
| complaints/support tickets | `backend/domains/complaints` |
| announcements | `backend/domains/announcements` |
| resources/comments | `backend/domains/resources` |
| schema/constraint/index | new revision under `database/alembic/versions` |
| role UI | matching `frontend/src/roles` page/panel |
| reusable UI behavior | `frontend/src/shared/ui` or `shared/lib` |
| workbook reconciliation | `backend/integrations/excel`, `scripts` |

## Removed Owners

Do not import or recreate these as compatibility shortcuts:

- `database/queries`
- `database/cross_queries`
- `database/tables.py`
- identity account/password/Telegram/parent facade modules under `backend/identity`
- `backend/roles/parent/services.py`
- `tgbot/helpers.py` and retired handler modules

## Remaining Compatibility Owners

- `backend/roles/admin`: existing admin page registry, HTML forms, and workspace helpers.
- selected `backend/roles/*/services.py` and workspace-card modules: page composition helpers pending domain/page migration.
- `backend/identity/storage.py`: owner/default startup seeding, using canonical account/domain APIs.
- legacy ID fields: migration/public-contract correlation only.

Before adding a feature, identify its page/API boundary, object policy, domain service, domain query owner, migration need, frontend owner, and verification command.
