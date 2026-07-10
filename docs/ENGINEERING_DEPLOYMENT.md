# Engineering Deployment

Audience: engineers preparing a reviewed release.

## Runtime Processes

`main.py` supports:

```bash
python3 main.py
python3 main.py web
python3 main.py bot
```

The web process serves FastAPI and built React assets. The bot process currently starts aiogram with an empty inbound router registry; Telegram Mini App authentication and parent linking are web flows and remain active without bot command handlers.

Web and bot can be separated into independent services later while sharing PostgreSQL.

## Database Deployment

`scripts/railway_start.sh` runs:

```bash
python -m alembic upgrade head
python main.py "$RUN_MODE"
```

Repository migration head is `0007_lms_integrity`. A failed migration stops startup. Test the entire chain on a disposable representative clone before release, especially the intentionally irreversible `0006_secure_parent_invites` revision.

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

Optional settings include database pool limits, `WEBAPP_INIT_DATA_TTL`, rate-limit/cache configuration, object storage, Teacher Academy notification chat IDs, and owner bootstrap credentials.

`ADMIN_PREVIEW_ROLES` is development-only and should be disabled for real role sessions.

## Pre-release Gate

- full backend tests and Python compile;
- Alembic upgrade on a disposable clone;
- route/architecture/identity tests;
- frontend tests, typecheck, and production build;
- browser responsive/accessibility/timezone smoke checks;
- Telegram Mini App login and parent invite smoke in a controlled environment;
- reviewed workbook reconciliation evidence if academic data changes are included;
- no `.env`, credentials, source workbooks, dumps, backups, or private reports staged.

Do not require an inbound bot-command smoke until handlers exist.

## Production Branch Rule

Production branch `main` is read-only during rewrite work. Do not merge, push, migrate, or deploy production as part of architecture cleanup without explicit release approval.
