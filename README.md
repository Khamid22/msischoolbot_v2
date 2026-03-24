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
- `COURSE_LEADER_CHAT` (optional for Contact US; numeric Telegram ID only, e.g. `123456789` or `-1001234567890`)
- `ADMIN_CHAT` (optional for Contact US; numeric Telegram ID only, e.g. `123456789` or `-1001234567890`)
- `FLASK_HOST` (default: `0.0.0.0`)
- `FLASK_PORT` (default: `8080`)
- `PORT` (overrides `FLASK_PORT`)
- `WAITRESS_THREADS` (default: `4`, used by production WSGI server)
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
- Sync runs at most once per UTC day (`students_sync_date` in `app_meta`) to reduce API usage.
- New students get generated unique IDs: `MSI#####`.
- Default password for new student is same as student ID.
- Password verification uses hashed values.

### Webhook-Based Sync (Recommended)

- Endpoint: `POST /webhooks/google-sheets`
- Auth header: `X-Webhook-Token: <your token>`
- Required env: `GOOGLE_SHEETS_WEBHOOK_TOKEN`
- Optional env:
- `SHEETS_WEBHOOK_CACHE_ENABLED=1` (force webhook cache mode; auto-enabled when token is set)
- `SHEETS_WEBHOOK_MAX_STALE_SECONDS=21600` (fallback hard refresh window when webhook is missed)

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

Run both bot + web:

```bash
python main.py
```

Or run separately:

Web:
```bash
python -m app.server
```

## Project Structure

- `config.py` - shared config
- `main.py` - starts Waitress (WSGI) web server thread + bot loop
- `bot/handlers/start.py` - `/start` handler
- `bot/keyboards/inline_keyboard.py` - inline keyboard builders
- `app/server.py` - Flask app, helpers, auth guard, route registration
- `app/services/auth_service.py` - auth + student/admin/teacher business logic
- `app/services/subject_summary_service.py` - daily Google Sheets -> SQLite subject summary sync
- `app/services/lesson_catalog_service.py` - daily Google Sheets -> SQLite lesson catalog sync
- `app/routes/home.py` - login/logout, home, search APIs
- `app/routes/dashboard.py` - dashboard endpoints
- `app/routes/rating_board.py` - rating board page
- `app/routes/webhooks.py` - Google Sheets webhook endpoint for cache invalidation + DB sync
- `app/integrations/sheets_data.py` - Google Sheets parser
