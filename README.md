# Telegram Mini App Sample (`aiogram` + `Flask`)

This project includes:
- Telegram bot on `aiogram` (polling mode)
- Mini App web backend/UI on `Flask`
- `initData` signature verification on backend

## 1) Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2) Configure environment

```bash
cp .env.example .env
```

Fill `.env`:
- `BOT_TOKEN`: token from `@BotFather`
- `MINI_APP_URL`: public HTTPS URL of your Flask app (required by Telegram)

For local testing you can use ngrok:

```bash
ngrok http 8080
```

Then set `MINI_APP_URL` to the generated `https://...` URL.

## 3) Run

Option A (recommended during development): run services separately in two terminals.

```bash
python -m web.app
```

```bash
python -m bot.main
```

Option B: run both from one process.

```bash
python main.py
```

## Railway Deploy (fix for 502)

1. Push this project with `Procfile` included.
2. In Railway service settings, set start command to `python -m web.app` (or keep auto-detected `Procfile`).
3. Set Railway environment variables:
   - `BOT_TOKEN`
   - `MINI_APP_URL` = your Railway public URL (e.g. `https://your-app.up.railway.app`)
   - `WEBAPP_INIT_DATA_TTL` (optional)
4. Do not hardcode local port for deploy. App now reads `PORT` automatically on Railway.
5. After deploy, verify:
   - `https://your-app.up.railway.app/health` returns `{"ok": true}`
6. Restart bot and send `/start` again so new buttons use current URL.

## 4) Test in Telegram

1. Send `/start` to your bot.
2. Tap `Open Mini App`.
3. In the Mini App, click `Verify initData on backend`.

If valid, Flask returns parsed Telegram user data from signed `initData`.
