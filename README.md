# MSI School LMS

MSI School LMS is a FastAPI, React, PostgreSQL, and Telegram Mini App system for school operations, academic departments, Teacher Academy workflows, student dashboards, parent access, and role-specific staff workspaces.

## Current Architecture

```text
frontend/                 React/Vite app
backend/                  FastAPI app, role routes, and business domains
database/                 PostgreSQL connection, schema bootstrap, migrations, and temporary query wrappers
tgbot/                    Telegram bot handlers
docs/                     active engineering and product documentation
```

Backend domain code lives under `backend/domains/`. Role-specific web routes live under `backend/roles/`. Temporary compatibility wrappers remain in `database/queries/`, `database/cross_queries/`, and selected `backend/identity/` modules while the database access layer is being separated.

The live database schema is still `msi_v2`. Do not rename it or edit schema objects without the reviewed schema migration plan.

## Main Docs

- `docs/CURRENT_ARCHITECTURE.md` - current backend/frontend/domain map and smoke checklist
- `docs/README.md` - documentation index
- `docs/GLOSSARY.md` - naming rules for confusing concepts
- `SCHEMA_RENAME_MSI_V2_TO_LMS_PLAN.md` - planned physical schema rename, not implemented

Historical phase plans are archived under `docs/archive/`.

## Run Locally

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Run the app:

```bash
python main.py
```

Run only the web backend:

```bash
python main.py web
```

Run only the Telegram bot:

```bash
python main.py bot
```

## Frontend

React source lives in `frontend/src`.

```bash
npm --prefix frontend run check-types
npm --prefix frontend run build
```

The build writes generated files into `backend/static/react/`. Do not edit generated build output manually.

## Verification

```bash
python3 -m pytest
npm --prefix frontend run check-types
npm --prefix frontend run build
git diff --check
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
