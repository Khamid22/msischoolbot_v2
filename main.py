import asyncio
import logging
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
from web.server import app, settings as web_settings


def run_flask():
    app.run(
        host=web_settings.flask_host,
        port=web_settings.flask_port,
        debug=False,
        use_reloader=False,
    )


async def run_bot():
    # Configure bot and start polling updates from Telegram.
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
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    asyncio.run(run_bot())
