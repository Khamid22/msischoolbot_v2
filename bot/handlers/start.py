import html

from aiogram import Router
from aiogram.filters import CommandStart

from bot.keyboards.inline_keyboard import registration_keyboard, student_menu_keyboard
from bot.settings import settings
from app.services.auth_service import get_student_by_telegram_user_id, record_bot_user

router = Router()


def _escape(value):
    return html.escape(str(value or ""))


def _linked_student_from_user(user):
    telegram_user_id = getattr(user, "id", None)
    if not isinstance(telegram_user_id, int):
        return None
    try:
        return get_student_by_telegram_user_id(telegram_user_id)
    except Exception:
        return None


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

    linked_student = _linked_student_from_user(message.from_user)
    if not linked_student:
        await message.answer(
            "👋 <b>Welcome!</b>\n\n"
            "Authentication is available only through the mini app.\n"
            "Please open the mini app and sign in first.",
            reply_markup=registration_keyboard(settings.mini_app_url),
        )
        return

    full_name = str(linked_student.get("full_name", "")).strip()
    if full_name:
        greeting = f"👋 <b>Welcome back, {_escape(full_name)}!</b>\n\nChoose an option:"
    else:
        greeting = "👋 <b>Welcome back!</b>\n\nChoose an option:"

    await message.answer(
        greeting,
        reply_markup=student_menu_keyboard(),
    )
