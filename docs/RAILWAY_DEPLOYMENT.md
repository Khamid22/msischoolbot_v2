# Railway Deployment

This project is ready to run on Railway as a FastAPI web service with a Railway
PostgreSQL database.

## What Railway Runs

The web service start command is:

```bash
python main.py web
```

The current `nixpacks.toml` / `railpack.json` install the React dependencies,
build the frontend, and then start the FastAPI backend.

## Required Railway Services

- Web service: this repository.
- PostgreSQL service: Railway Postgres.
- Optional Redis service: only if you want persistent SlowAPI rate-limit storage.

## Required Variables

Use `.env.railway.example` as the checklist. Do not paste local `.env` blindly.

Important production values:

```bash
RUN_MODE=web
APP_ENV=production
APP_SECRET_KEY=<strong random secret>
SESSION_COOKIE_SECURE=1
SESSION_COOKIE_SAMESITE=lax
DATABASE_URL=${{Postgres.DATABASE_URL}}
DEMO_AUTH_ENABLED=0
```

Generate `APP_SECRET_KEY` locally:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

## CLI Flow

Railway CLI must be logged in first:

```bash
railway login
railway whoami
```

Create/link a project:

```bash
railway init
```

Add PostgreSQL:

```bash
railway add --database postgres
```

Set variables in Railway Dashboard or with CLI:

```bash
railway variables set RUN_MODE=web APP_ENV=production DEMO_AUTH_ENABLED=0
railway variables set APP_SECRET_KEY=<secret>
railway variables set DATABASE_URL='${{Postgres.DATABASE_URL}}'
```

Deploy:

```bash
railway up
railway domain
```

After Railway gives a domain, update:

```bash
railway variables set MINI_APP_URL=https://your-domain.up.railway.app
```

## Copy Local PostgreSQL Data To Railway

Use the safe copy script. It creates a local dump and refuses to restore into a
non-empty target database.

```bash
python3 scripts/copy_postgres_to_railway.py \
  --source "$LOCAL_DATABASE_URL" \
  --target "$RAILWAY_DATABASE_PUBLIC_URL"
```

Notes:

- `source` is your current local/production PostgreSQL URL.
- `target` must be the Railway Postgres public connection URL.
- The script does not delete local data.
- The script refuses non-empty Railway databases to avoid accidental overwrite.

## Safety

Never run destructive SQL against either database during migration. If the target
database already has tables, create a fresh Railway Postgres service or take an
explicit backup plan before continuing.
