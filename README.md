# Telegram School Dashboard (Aiogram + Flask)

This project has three parts:
- Telegram bot (`aiogram`) in `telegram_bot/`
- Backend dashboard app (`Flask`) in `web/backend/`
- Frontend (React + Vite) in `web/frontend/`

Shared database access lives in `database_storage/`. The bot opens the web app
as a Telegram Mini App.

## Dependencies

Use the root requirements file as the single source of dependencies:

```bash
pip install -r requirements.txt
```

## Environment Variables

Create `.env` in the project root:
- `BOT_TOKEN`
- `MINI_APP_URL`
- `ENABLE_TEST_ADMIN_LOGIN` (optional; `1`/`0`, default: `1`; enables `/admin` + Admin(Test) button)
- `TEST_ADMIN_LOGIN` (optional; default: `staff280902`)
- `TEST_ADMIN_PASSWORD` (optional; default falls back to `OWNER_ADMIN_PASSWORD`)
- `TEST_ADMIN_TELEGRAM_IDS` (optional comma-separated allowlist for test admin login)
- `COURSE_LEADER_CHAT` (optional for Contact US; numeric Telegram ID only, e.g. `123456789` or `-1001234567890`)
- `ADMIN_CHAT` (optional for Contact US; numeric Telegram ID only, e.g. `123456789` or `-1001234567890`)
- `FLASK_HOST` (default: `0.0.0.0`)
- `FLASK_PORT` (default: `8080`)
- `PORT` (overrides `FLASK_PORT`)
- `WAITRESS_THREADS` (default: `max(16, cpu_count * 8)`, used by production WSGI server)
- `WAITRESS_CONNECTION_LIMIT` (default: `1024`)
- `WAITRESS_CHANNEL_TIMEOUT` (default: `120`)
- `RUN_MODE` (`both`, `web`, `bot`; default: `both`)
- `STUDENT_METADATA_CACHE_SECONDS` (default: `30`, cache `/api/metadata` payload)
- `STUDENT_PANEL_CONTEXT_CACHE_SECONDS` (default: `30`, cache student home panel context)
- `ADMIN_PAGE_CONTEXT_CACHE_SECONDS` (default: `15`, cache admin panel context)
- `FLASK_SECRET_KEY` (recommended for secure Flask session cookies)
- `GROUP_CACHE_TTL_SECONDS` (default: `600`)
- `DATABASE_URL` (required PostgreSQL URL)
- `R2_ENABLED` (optional; `1`/`0`, default: `1`; set `0` for local/dev to disable R2 uploads)
- `OWNER_ADMIN_LOGIN` (default: `staff280902`)
- `OWNER_ADMIN_PASSWORD` (default: `Khamid007`)

Database backend behavior:
- Local development and production both use PostgreSQL through `DATABASE_URL`.
- `POSTGRES_DB` is only the database name, not a full connection URL.
- Railway video processing: this repo includes `railpack.json` to install `ffmpeg`. If your service overrides build config, add `RAILPACK_DEPLOY_APT_PACKAGES=ffmpeg`.
- Local development storage: set `R2_ENABLED=0` and keep `R2_*` credentials unset to avoid writing to production bucket.

## Auth Flow

1. Open `/` (home page).
2. Login by prefix:
- `staff#####` -> admin path
- `MSI#####` -> student path
3. Credentials are checked against PostgreSQL.
4. Authenticated users get a Flask session.
5. Student login redirects directly to their own dashboard.
6. All protected pages and APIs require an authenticated session.
7. Student access to dashboard/rating URLs is restricted to their own student ID.

## Panels

- Admin panel shows:
- bot users count (from `bot_users` table)
- students table: full name, enrolled course, student ID, password

- Student panel keeps existing behavior:
- direct open to own dashboard after login
- student cannot open another student ID directly

## Students

- Students live in PostgreSQL and are managed from the admin panel.
- New students get generated unique IDs: `MSI#####`.
- Default password for a new student is the same as their student ID.
- Password verification uses hashed values.

## PostgreSQL Tables

Main tables used for auth and admin data:
- `admins`
- `students` (required columns: ID, Full Name, Student ID, Password, Subjects, Telegram User ID)
- `student_auth` (hashed password storage)
- `students_sheet_map` (maps public dashboard id -> student row id)
- `bot_users`
- `app_meta`
- `subject_summaries` (daily snapshot for bot quick summary: subject, AAP, AR, EP, rating, total coins)
- `lesson_catalog` (daily snapshot of lesson number/topic per subject for AAP lesson table)

## Run Locally

Run both bot + web in one process (dev only):

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

Recommended in production (separate processes):

```bash
# terminal 1
python main.py web

# terminal 2
python main.py bot
```

## Project Structure

See `docs/architecture.md` for the current backend boundaries and rules for new
work.

- `config.py` - shared config
- `main.py` - starts the web server (gevent/Flask) and/or the bot polling loop
- `telegram_bot/handlers/` - bot command and callback handlers (`start`, `account_link`, `quick_summary`, `contact_us`)
- `telegram_bot/keyboards/inline_keyboard.py` - inline keyboard builders
- `web/backend/server.py` - Flask app, helpers, auth guard, route registration
- `web/backend/routes/` - HTTP route modules (students, admin, system)
- `web/backend/services/` - business workflows (auth, resources, subjects, academic, announcements, dashboards)
- `web/backend/queries/` - reusable SQL helpers
- `database_storage/` - PostgreSQL connection layer, table schema, and shared queries
- `web/frontend/` - React + Vite mini app source (built into `web/backend/static/`)
