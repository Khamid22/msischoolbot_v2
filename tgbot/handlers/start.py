from aiogram import Router
from aiogram.filters import Command, CommandStart

from tgbot.keyboards.inline_keyboard import start_menu_keyboard, student_menu_keyboard
from tgbot.settings import settings
from shared.identity.account_service import record_bot_user

router = Router()


async def _send_start_payload(message):
    await message.answer(
        "👋 <b>Welcome!</b>\n\n"
        "Open the mini app to continue, or use the quick bot tools below.\n\n"
        "Student credentials continue in the mini app.\n"
        "Admin credentials redirect to the website.",
        reply_markup=start_menu_keyboard(settings.mini_app_url),
    )


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

    await _send_start_payload(message)


@router.message(Command("menu"))
async def menu_handler(message):
    await message.answer(
        "📌 <b>Bot tools</b>\n"
        "Use the buttons below for quick actions:",
        reply_markup=student_menu_keyboard(),
    )
