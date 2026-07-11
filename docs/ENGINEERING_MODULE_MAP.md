# Engineering Module Map

Audience: engineers locating the current owner of a change.

## Repository Map

```text
backend/application/              FastAPI composition
backend/workspaces/               seven business workspace adapters
backend/internal_operations/      protected System Admin adapters
backend/modules/accounts/         identity, password, Telegram account auth
backend/modules/academics/        schools, programs, groups, gradebook, schedule
backend/modules/communications/   announcements and chat
backend/modules/complaints/       complaints and support workflow
backend/modules/learning_resources/ resources and comments
backend/modules/parent_access/    parents, invites, linked-child access
backend/modules/payments/         payment rules and persistence
backend/modules/reporting/        dashboards, summaries, cross-feature read models
backend/modules/staff_records/    teachers, candidates, staff development
backend/modules/student_records/  student profiles, dashboard, activity
backend/core/                     config, database, session, guards, rendering
backend/integrations/             Telegram and object storage
database/alembic/                 all schema DDL and migration history

frontend/src/app/                 bootstrap and lazy page registry
frontend/src/workspaces/          seven business workspace entry pages
frontend/src/features/            reusable business workflows
frontend/src/internal_operations/ protected System Admin UI
frontend/src/shared/              routes, API, time, motion, accessible UI
```

## Change Routing

| Change | Primary owner |
| --- | --- |
| account/password/session | `backend/modules/accounts` |
| role normalization/guards | `backend/core/access`, `backend/core/guards.py` |
| workspace composition | matching package under `backend/workspaces` |
| schools/groups/programs/gradebook/schedules | `backend/modules/academics` |
| executive/academic summaries | `backend/modules/reporting` |
| students and dashboard payload | `backend/modules/student_records` |
| parents, invites, linked-child access | `backend/modules/parent_access` |
| teachers/candidates/Teacher Academy records | `backend/modules/staff_records` |
| payments | `backend/modules/payments` |
| chat/announcements | `backend/modules/communications` |
| complaints | `backend/modules/complaints` |
| resources/comments | `backend/modules/learning_resources` |
| System Admin UI/forms | `backend/internal_operations`, `frontend/src/internal_operations` |
| schema/constraint/index | new revision under `database/alembic/versions` |
| business workspace UI | matching `frontend/src/workspaces` package |
| reusable business UI | `frontend/src/features` |
| reusable UI behavior | `frontend/src/shared/ui` or `frontend/src/shared/lib` |

## Removed Owners

Do not import or recreate:

- `backend/api`
- `backend/pages`
- `backend/services`
- `backend/repositories`
- `backend/schemas`
- `frontend/src/roles`
- Teacher portal page/API/navigation packages
- Excel or Google Sheets import/reconciliation packages

Before adding a feature, identify its workspace/API adapter, object policy, public module contract, owning repository, migration need, frontend feature/workspace owner, and tests.
