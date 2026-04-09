from aiogram import Router
from aiogram.filters import CommandStart

from bot.keyboards.inline_keyboard import registration_keyboard
from bot.settings import settings
from app.routes.students.services.auth_service import record_bot_user

router = Router()


@router.message(CommandStart())
async def start_handler(message, state):
    # Clear any pending FSM state when user starts over.
    await state.clear()

    # Track unique bot users for admin statistics.
    try:
        record_bot_user(message.from_user)
    except Exception:
        # Do not fail /start if SQLite write has an issue.
        pass

    await message.answer(
        "👋 <b>Welcome!</b>\n\n"
        "Tap the button below to open the mini app.\n\n"
        "Student credentials continue in the mini app.\n"
        "Admin credentials redirect to the website.",
        reply_markup=registration_keyboard(settings.mini_app_url),
    )
