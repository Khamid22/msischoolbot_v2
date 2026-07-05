# MSI School Bot And Portal

This project has four runtime areas:

- `tgbot/` - Telegram bot only
- `web/backend/` - FastAPI backend only
- `web/frontend/` - React frontend only
- `shared/` - Python logic and PostgreSQL access shared by bot and backend

PostgreSQL is the source of truth. Do not delete database values during cleanup.

## Architecture

```text
web/frontend -> web/backend -> shared -> shared/db -> PostgreSQL
tgbot -----------------------> shared -> shared/db -> PostgreSQL
```

The bot and web backend must not import each other.

## Current Source Map

```text
shared/
  academics/        subject, date, school, and summary rules
  identity/         login, passwords, profiles, Telegram links
  db/               PostgreSQL connection, tables, shared SQL queries

tgbot/
  handlers/         aiogram command/callback handlers
  keyboards/        Telegram inline keyboard builders
  helpers.py        bot-specific formatting helpers

web/backend/
  server.py         FastAPI app composition
  routes/           small system routes
  roles/            role-specific backend workflows
  domains/          reusable backend business domains
  utils/            web-only helpers
  static/react/     generated React build output

web/frontend/src/
  app/              React app bootstrap
  shared/           reusable frontend UI and browser helpers
  roles/            role-specific React screens
```

## Main Docs

- `AGENTS.md` - rules for coding assistants
- `docs/README.md` - MSI LMS Portal documentation index
- `docs/GLOSSARY.md` - naming rules for confusing concepts

## Run Locally

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Run both web and bot:

```bash
python main.py
```

Run only web:

```bash
python main.py web
```

Run only bot:

```bash
python main.py bot
```

## Frontend

React source lives in `web/frontend/src`.

Check and build:

```bash
cd web/frontend
npm run check-types
npm run build
```

The build writes generated files into `web/backend/static/react/`. Do not edit
that generated folder manually.

## Verification

Backend/import check:

```bash
python3 -m compileall -q shared tgbot web/backend scripts main.py
python3 - <<'PY'
from web.backend.server import app
print(app.name)
PY
```

Frontend check:

```bash
cd web/frontend
npm run check-types
npm run build
```

## Environment

Required:

- `DATABASE_URL`
- `BOT_TOKEN`
- `MINI_APP_URL`
- `APP_SECRET_KEY`

Common optional settings:

- `RUN_MODE` (`both`, `web`, or `bot`)
- `WEB_HOST`
- `WEB_PORT`
- `PORT`
- `DB_POOL_MIN`
- `DB_POOL_MAX`
- `REDIS_URL`
- `R2_ENABLED`
- `OWNER_ADMIN_LOGIN`
- `OWNER_ADMIN_PASSWORD`
