# Engineering Deployment

Audience: engineers preparing a reviewed release.

## Runtime Processes

`main.py` supports:

```bash
python3 main.py
python3 main.py web
python3 main.py bot
python3 main.py worker
```

The web process serves FastAPI and built React assets. The bot process owns the aiogram portal
entry flow. The worker claims typed outbox jobs in bounded PostgreSQL batches and runs module-owned
handlers.

Deploy web, bot, and worker as independent services sharing PostgreSQL. Do not run durable job
polling inside a web replica. The LMS services use the `FastAPI-Run-System` branch and Railway's
`development` environment; the Railway `main` environment is out of scope.

## Railway Service Topology

The LMS is deployed from one repository and branch. Services are process boundaries, not Git
branches:

```text
LMS-Frontend     -> public ingress, React assets, same-origin backend proxy
LMS-Backend      -> FastAPI, database migrations, embedded curriculum conversion
LMS-Telegram-Bot -> aiogram polling and its internal readiness endpoint
finance-worker   -> existing payment worker; managed separately
Postgres         -> shared system of record
```

Each LMS service selects its matching file under `deploy/` as its Railway config-as-code path.
Only the backend configuration runs Alembic. The frontend receives no application secrets and the
bot has no public domain.

## Database Deployment

`scripts/railway_start.sh` starts the selected process:

```bash
python main.py "$RUN_MODE"
```

Database migration is a separate reviewed release step. The repository head is
`0049_billing_reliability`. Before applying it to production, run `python -m alembic current`
against production and require `0048_billing_enforcement` (or `0049_billing_reliability` when
already applied). Stop if production is behind `0048`: earlier recruitment-catalog revisions
contain row deletions and require a separate data review and explicit approval.

Test the entire chain on a disposable representative clone before release, especially
intentionally irreversible revisions. A migration failure must stop the release.

Never substitute manual production DDL for a migration.

## Frontend Build

```bash
npm --prefix frontend run check-types
npm --prefix frontend run build
```

Vite writes generated files under `backend/static/react`. Do not manually edit generated assets.

## Environment Categories

Do not place values in documentation or Git.

Required deployed settings include:

- PostgreSQL connection (`DATABASE_URL`);
- application/session secret (`APP_SECRET_KEY`);
- Telegram bot token and Mini App URL;
- host/port/runtime mode.

Optional settings include database pool limits, `WEBAPP_INIT_DATA_TTL`, rate-limit/cache
configuration, object storage, Teacher Academy notification chat IDs, and `WORKER_*` batch,
polling, lease, and retry settings. `WORKER_ALLOWED_TOPICS` is a comma-separated exact allowlist;
an empty value permits all registered topics.

## Staged Finance Worker

Do not create or enable a production worker as part of the web deployment. First deploy the web
code and migration, then review:

```text
GET /api/v1/customer-support/payments/automation-status
```

The report must be checked for due profiles, invoices without enforcement schedules, Telegram
coverage, delivery failures, active payment-only holds, and the last successful finance-worker
activity.

Starting the dedicated Railway finance worker requires explicit approval because queued jobs can
create invoices, send Telegram messages, and restrict real accounts. Its initial exact allowlist
is:

```text
finance.generate_invoices
finance.bootstrap_billing_enforcement
finance.process_billing_enforcement_stage
finance.send_billing_notification
finance.reconcile_billing_enforcement
finance.reconcile_legacy_payments
```

Configure these as a comma-separated `WORKER_ALLOWED_TOPICS` value. Keep Payme disabled until new
sandbox credentials are supplied through production environment variables; never place Payme
credentials in Git or documentation.

## Pre-release Gate

- full backend tests and Python compile;
- Alembic upgrade on a disposable clone;
- route/architecture/identity tests;
- frontend tests, typecheck, and production build;
- browser responsive/accessibility/timezone smoke checks;
- Telegram Mini App login and parent invite smoke in a controlled environment;
- reviewed workbook reconciliation evidence if academic data changes are included;
- no `.env`, credentials, source workbooks, dumps, backups, or private reports staged.

Smoke-test the bot portal-entry command and one controlled worker job before release.

## Protected Environment Rule

GitHub and Railway `main` are read-only during rewrite work. LMS releases use the
`FastAPI-Run-System` branch and Railway `development` environment. Do not merge, push, migrate, or
deploy `main` as part of architecture cleanup without explicit release approval.
