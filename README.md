# MSI School LMS

MSI School LMS is a PostgreSQL-first school portal built with FastAPI and React. It provides role-specific workspaces for students, parents, teachers, academic staff, support staff, executives, and system administrators. Telegram remains an authenticated Mini App/integration surface; it is no longer the architecture of the LMS itself.

## Architecture at a Glance

```text
frontend/                 React/Vite role pages and shared UI primitives
backend/api/v1/           versioned JSON/action endpoints
backend/pages/            server-rendered React page bootstraps
backend/domains/          business services and domain-owned SQL
backend/core/             PostgreSQL connection and application configuration
backend/integrations/     Telegram, Excel, and storage adapters
backend/security/         session, role, and permission enforcement
database/alembic/         the only owner of schema DDL
tgbot/                    Telegram worker shell; inbound router registry is empty
scripts/                  deployment and explicit reconciliation/import tools
tests/                    backend, route, migration, and architecture coverage
```

The runtime dependency direction is:

```text
React / Telegram Mini App -> FastAPI routes -> domain services -> domain queries -> PostgreSQL
explicit import tools -----------------------> reconciliation boundary ---------> PostgreSQL
```

PostgreSQL schema `msi_v2` is the source of truth. Google Sheets and the old Telegram mini-app workflow are not live academic-data backends. Spreadsheet files are accepted only through explicit import/reconciliation tooling; a successful source-parity result must come from a completed reconciliation run, not from documentation.

## Architecture Invariants

- `msi_v2.accounts` is the sole password authority. Role profiles point to the canonical account.
- A newly provisioned password account may start with `password == login`; `must_change_password` blocks workspace access until the user changes it at `/account/security`.
- `PATCH /api/v1/auth/password` is the self-service password endpoint for every password-enabled role.
- Sessions carry `account_id`, canonical role, and `session_version`. Password resets, role changes, and account disablement invalidate older cookies.
- Backend authorization uses canonical `msi_v2.students.id`. Legacy row IDs and public dashboard/enrollment IDs remain only at explicit compatibility boundaries.
- Runtime code does not create or alter tables. Apply schema changes with Alembic; current migration head is `0007_lms_integrity`.
- SQL is owned by `backend/domains/*/queries.py`. The old `database/queries`, `database/cross_queries`, `database/tables`, and identity compatibility facades have been removed.
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

For workbook reconciliation, use `scripts/reconcile_academic_workbooks.py` in dry-run/reporting mode first. Never infer that School 5 or Sehriyo data matches merely because a workbook parsed successfully.

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
- [API migration status](docs/API_MIGRATION_STATUS.md)
- [Architecture cleanup report](docs/ARCHITECTURE_CLEANUP_2026-07-10.md)
- [Documentation index](docs/README.md)

Production branch `main` is reference-only during rewrite work. Do not modify or deploy it from the rewrite task without explicit approval.
