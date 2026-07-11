# MSI School LMS

MSI School LMS is a PostgreSQL-first school portal built with FastAPI and React. It provides seven business workspaces: CEO, Academic Director, Head of Departments, Customer Support, HR Manager, Student, and Parent. Teachers are staff records managed inside authorized workspaces; they do not have a portal workspace or login role. System Admin is a protected internal-operations boundary, not an eighth business workspace.

## Architecture at a Glance

```text
frontend/src/workspaces/  the seven business workspace adapters
frontend/src/features/    reusable business UI and workflows
frontend/src/shared/      shared UI, routing, time, and API primitives
backend/application/      FastAPI composition and route registration
backend/workspaces/       the seven business HTTP/page adapters
backend/modules/          independent business modules and module-owned SQL
backend/internal_operations/ protected System Admin operations
backend/core/             configuration, PostgreSQL, sessions, and security
backend/integrations/     Telegram and storage adapters
database/alembic/         the only owner of schema DDL
tgbot/                    Telegram worker shell; inbound router registry is empty
scripts/                  deployment and explicit reconciliation/import tools
tests/                    backend, route, migration, and architecture coverage
```

The runtime dependency direction is:

```text
React / Telegram Mini App -> workspace/API adapter -> module service -> module repository -> PostgreSQL
internal operations ------> shared module contracts --------------------------------------^
```

PostgreSQL schema `msi_v2` is the only runtime source of truth. Google Sheets, Excel workbooks, and the old Telegram mini-app workflow are not LMS data integrations.

## Architecture Invariants

- `msi_v2.accounts` is the sole password authority. Role profiles point to the canonical account.
- A newly provisioned password account may start with `password == login`; `must_change_password` blocks workspace access until the user changes it at `/account/security`.
- `PATCH /api/v1/auth/password` is the self-service password endpoint for every password-enabled role.
- Sessions carry `account_id`, canonical role, and `session_version`. Password resets, role changes, and account disablement invalidate older cookies.
- Backend authorization uses canonical `msi_v2.students.id`. Legacy row IDs and public dashboard/enrollment IDs remain only at explicit compatibility boundaries.
- Runtime code does not create or alter tables. Apply schema changes with Alembic; current migration head is `0008_remove_teacher_portal`.
- SQL is owned by the matching package under `backend/modules`. Workspace and application adapters contain no SQL.
- Business modules communicate through public service/contract functions, never by importing another module's repository.
- The deleted `backend/api`, `backend/pages`, `backend/services`, `backend/repositories`, and `backend/schemas` trees must not be recreated.
- Parent invite codes are random, expiring, single-use, hashed at rest, and consumed inside the same transaction that creates the parent link and canonical identity.
- Telegram `initData` is HMAC-verified with a replay window before it can identify a user.
- School calendar and office-hour UI logic use `Asia/Tashkent`; unknown source times are not invented.

## Run Locally

Install dependencies and apply migrations:

```bash
pip install -r requirements.txt
python -m alembic upgrade head
```

Run both services, the web service, or the Telegram worker shell:

```bash
python main.py
python main.py web
python main.py bot
```

The bot command registry is intentionally empty at present. Telegram authentication and Mini App parent linking continue to work through the web application.

## Frontend

React source lives in `frontend/src`. The build writes generated assets to `backend/static/react/`; do not edit generated output manually.

```bash
npm --prefix frontend run test:logic
npm --prefix frontend run test:schedule
npm --prefix frontend run test:shared-ui
npm --prefix frontend run test:academic
npm --prefix frontend run check-types
npm --prefix frontend run build
```

## Verification

```bash
python3 -m pytest
python3 -m compileall -q backend database tgbot scripts main.py
npm --prefix frontend run check-types
npm --prefix frontend run build
git diff --check
```

## Environment

Required in deployed environments:

- `DATABASE_URL`
- `BOT_TOKEN`
- `MINI_APP_URL`
- `APP_SECRET_KEY`

Common optional settings include `RUN_MODE`, `WEB_HOST`, `WEB_PORT`, `PORT`, database pool settings, `WEBAPP_INIT_DATA_TTL`, `REDIS_URL`, storage settings, and owner bootstrap credentials.

## Documentation

- [Current architecture](docs/CURRENT_ARCHITECTURE.md)
- [Authentication and roles](docs/ENGINEERING_AUTH_AND_ROLES.md)
- [Database architecture](docs/ENGINEERING_DATABASE.md)
- [Engineering architecture](docs/ENGINEERING_ARCHITECTURE.md)
- [Module map](docs/ENGINEERING_MODULE_MAP.md)
- [Documentation index](docs/README.md)

Production branch `main` is reference-only during rewrite work. Do not modify or deploy it from the rewrite task without explicit approval.
