import asyncio
import logging
import os
import threading

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import (
    MenuButtonWebApp,
    WebAppInfo,
)

from bot.handlers.contact_us import router as contact_us_router
from bot.handlers.quick_summary import router as quick_summary_router
from bot.handlers.start import router as start_router
from bot.settings import settings as bot_settings
from waitress import serve
from app.main import app, settings as web_settings
from app.services.auth_service import init_storage


def _waitress_threads():
    raw_value = str(os.getenv("WAITRESS_THREADS", "4") or "").strip()
    try:
        parsed = int(raw_value)
    except ValueError:
        logging.warning("Invalid WAITRESS_THREADS=%r, using 4", raw_value)
        return 4
    return max(parsed, 1)


def run_web_server():
    serve(
        app,
        host=web_settings.flask_host,
        port=web_settings.flask_port,
        threads=_waitress_threads(),
    )


async def run_bot():
    logging.basicConfig(level=logging.INFO)

    bot = Bot(
        token=bot_settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(start_router)
    dp.include_router(quick_summary_router)
    dp.include_router(contact_us_router)

    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(
            text="Mini App",
            web_app=WebAppInfo(url=bot_settings.mini_app_url),
        )
    )
    await dp.start_polling(bot)


if __name__ == "__main__":
    init_storage()
    flask_thread = threading.Thread(target=run_web_server, daemon=True)
    flask_thread.start()
    asyncio.run(run_bot())
