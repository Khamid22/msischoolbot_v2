import asyncio
import logging

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MenuButtonWebApp,
    Message,
    WebAppInfo,
)

from config import get_settings
from web.auth_store import record_bot_user

router = Router()
settings = get_settings()


@router.message(CommandStart())
async def start_handler(message):
    # Send Telegram button that opens the web mini app.
    # Track unique bot users for admin statistics.
    try:
        record_bot_user(message.from_user)
    except Exception:
        # Do not fail /start if SQLite write has an issue.
        pass

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Open Mini App",
                    web_app=WebAppInfo(url=settings.mini_app_url),
                )
            ]
        ]
    )
    await message.answer(
        "Welcome! 👋\n\nClick the button below to open the Student Performance Dashboard and review attendance and academic results.",
        reply_markup=keyboard,
    )

async def run_bot():
    # Configure bot and start polling updates from Telegram.
    logging.basicConfig(level=logging.INFO)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(router)

    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(
            text="Mini App",
            web_app=WebAppInfo(url=settings.mini_app_url),
        )
    )
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(run_bot())
