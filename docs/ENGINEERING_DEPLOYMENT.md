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
polling inside a web replica.

## Database Deployment

`scripts/railway_start.sh` runs:

```bash
python -m alembic upgrade head
python main.py "$RUN_MODE"
```

Repository migration head is `0044_student_identifier_sequence`. A failed migration stops startup. Test the
entire chain on a disposable representative clone before release, especially intentionally
irreversible revisions.

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
polling, lease, and retry settings.

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

## Production Branch Rule

Production branch `main` is read-only during rewrite work. Do not merge, push, migrate, or deploy production as part of architecture cleanup without explicit release approval.
