# Telegram School Dashboard (Aiogram + Flask)

This project has two parts:
- Telegram bot (`aiogram`) in `bot/`
- Backend dashboard app (`Flask`) in `app/`
- Frontend assets/templates in `app/web/`

The bot opens the web app as a Telegram Mini App.

## Dependencies

Use the root requirements file as the single source of dependencies:

```bash
pip install -r requirements.txt
```

`app/requirements.txt` points to the root requirements file.

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
- `DISABLE_BACKGROUND_REFRESH` (optional; `1` disables startup Sheets background refresh)
- `GOOGLE_SHEETS_WEBHOOK_TOKEN` (required for webhook auth)
- `SHEETS_WEBHOOK_CACHE_ENABLED` (optional; defaults to enabled when token is set)
- `SHEETS_WEBHOOK_MAX_STALE_SECONDS` (default: `21600`)
- `STUDENT_METADATA_CACHE_SECONDS` (default: `30`, cache `/api/metadata` payload)
- `STUDENT_PANEL_CONTEXT_CACHE_SECONDS` (default: `30`, cache student home panel context)
- `ADMIN_PAGE_CONTEXT_CACHE_SECONDS` (default: `15`, cache admin panel context)
- `FLASK_SECRET_KEY` (recommended for secure Flask session cookies)
- `GROUP_CACHE_TTL_SECONDS` (default: `600`)
- `AUTH_DB_PATH` (optional path for SQLite, default: `utils/app_data.sqlite3`)
- `OWNER_ADMIN_LOGIN` (default: `staff280902`)
- `OWNER_ADMIN_PASSWORD` (default: `Khamid007`)

## Auth Flow

1. Open `/` (home page).
2. Login by prefix:
- `staff#####` -> admin path
- `MSI#####` -> student path
3. Credentials are checked against SQLite.
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

## Student Sync From Google Sheets

- Students are synced from Google Sheets into SQLite.
- Sync is webhook-driven and runs in an in-process background thread.
- New students get generated unique IDs: `MSI#####`.
- Default password for new student is same as student ID.
- Password verification uses hashed values.

### Webhook-Based Sync (Recommended)

- Endpoint: `POST /webhooks/google-sheets`
- Auth header: `X-Webhook-Token: <your token>`
- Required env: `GOOGLE_SHEETS_WEBHOOK_TOKEN`
- Behavior: endpoint returns immediately (`202`) and sync runs in background.
- Optional env:
- `SHEETS_WEBHOOK_CACHE_ENABLED=1`
- `SHEETS_WEBHOOK_MAX_STALE_SECONDS=21600`

Webhook payload supports one or many schools:

```json
{
  "school": "sehriyo"
}
```

```json
{
  "schools": ["school5", "sehriyo"]
}
```

```json
{
  "spreadsheetId": "your_google_spreadsheet_id"
}
```

### Google Sheets Trigger Setup (Apps Script)

Google Sheets does not push webhooks natively. Use Apps Script installable triggers.

1. Open your spreadsheet -> Extensions -> Apps Script.
2. Paste `scripts/google_sheets_webhook.gs` into the project.
3. In Script Properties, set:
- `WEBHOOK_URL=https://<your-domain>/webhooks/google-sheets`
- `WEBHOOK_TOKEN=<same value as GOOGLE_SHEETS_WEBHOOK_TOKEN>`
4. Run `setupInstallableTriggers()` once and grant permissions.
5. Optionally run `testWebhook()` to verify the endpoint returns success.

## SQLite Tables

Main tables used for auth and admin data:
- `admins`
- `students` (required columns: ID, Full Name, Student ID, Password, Subjects, Telegram User ID)
- `student_auth` (hashed password storage)
- `students_sheet_map` (Google Sheets student mapping)
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

- `config.py` - shared config
- `main.py` - starts Waitress (WSGI) web server thread + bot loop
- `bot/handlers/start.py` - `/start` handler
- `bot/keyboards/inline_keyboard.py` - inline keyboard builders
- `app/server.py` - Flask app, helpers, auth guard, route registration
- `app/routes/students/services/auth_service.py` - auth + student/admin/teacher business logic
- `app/routes/students/services/subject_summary_service.py` - daily Google Sheets -> SQLite subject summary sync
- `app/routes/students/services/lesson_catalog_service.py` - daily Google Sheets -> SQLite lesson catalog sync
- `app/routes/home.py` - login/logout, home, search APIs
- `app/routes/dashboard.py` - dashboard endpoints
- `app/routes/rating_board.py` - rating board page
- `app/routes/webhooks.py` - Google Sheets webhook endpoint for cache invalidation + DB sync
- `app/integrations/sheets_data.py` - Google Sheets parser
