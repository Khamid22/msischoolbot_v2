import html
import os

from aiogram import Router
from aiogram.filters import CommandStart

from bot.keyboards.inline_keyboard import registration_keyboard, student_menu_keyboard
from bot.settings import settings
from app.routes.students.services.auth_service import (
    get_admin_by_telegram_user_id,
    get_student_by_telegram_user_id,
    record_bot_user,
)

router = Router()


def _escape(value):
    return html.escape(str(value or ""))


def _is_test_admin_login_enabled():
    raw_value = str(os.environ.get("ENABLE_TEST_ADMIN_LOGIN", "1") or "").strip().casefold()
    return raw_value in {"1", "true", "yes", "on"}


def _linked_student_from_user(user):
    telegram_user_id = getattr(user, "id", None)
    if not isinstance(telegram_user_id, int):
        return None
    try:
        return get_student_by_telegram_user_id(telegram_user_id)
    except Exception:
        return None


def _linked_admin_from_user(user):
    telegram_user_id = getattr(user, "id", None)
    if not isinstance(telegram_user_id, int):
        return None
    try:
        return get_admin_by_telegram_user_id(telegram_user_id)
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

    linked_admin = _linked_admin_from_user(message.from_user)
    if linked_admin:
        admin_login = str(linked_admin.get("login", "")).strip()
        admin_role = str(linked_admin.get("role", "admin")).strip() or "admin"
        admin_line = f"Login: <b>{_escape(admin_login)}</b>\n" if admin_login else ""
        await message.answer(
            "🛡️ <b>Admin status: active</b>\n\n"
            f"{admin_line}"
            f"Role: <b>{_escape(admin_role)}</b>\n\n"
            "Use the mini app to open the admin panel.",
            reply_markup=registration_keyboard(settings.mini_app_url),
        )
        return

    linked_student = _linked_student_from_user(message.from_user)
    if not linked_student:
        test_admin_enabled = _is_test_admin_login_enabled()
        hint_line = (
            "\n\nFor testing without Mini App, use <code>/admin</code> or tap <b>Admin (Test)</b>."
            if test_admin_enabled
            else ""
        )
        await message.answer(
            "👋 <b>Welcome!</b>\n\n"
            "Authentication is available only through the mini app.\n"
            "Please open the mini app and sign in first."
            f"{hint_line}",
            reply_markup=registration_keyboard(
                settings.mini_app_url,
                show_test_admin=test_admin_enabled,
            ),
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
