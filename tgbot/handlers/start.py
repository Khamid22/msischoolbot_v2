from aiogram import Router
from aiogram.filters import Command, CommandStart

from tgbot.keyboards.inline_keyboard import (
    parent_invite_keyboard,
    start_menu_keyboard,
    student_menu_keyboard,
)
from tgbot.settings import settings
from shared.identity.account_service import record_bot_user
from shared.identity.parent_accounts import link_parent_via_invite
from shared.identity.parent_invites import load_parent_invite_code_payload

router = Router()


def _start_payload(message):
    text = str(getattr(message, "text", "") or "").strip()
    parts = text.split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ""


def _parent_invite_url(code):
    return f"{settings.mini_app_url.rstrip('/')}/parent/invite/{code}"


def _telegram_parent_profile(user):
    first_name = str(getattr(user, "first_name", "") or "").strip()
    last_name = str(getattr(user, "last_name", "") or "").strip()
    username = str(getattr(user, "username", "") or "").strip().lstrip("@")
    full_name = " ".join(part for part in (first_name, last_name) if part).strip()
    telegram_user_id = getattr(user, "id", None)
    try:
        telegram_user_id = int(telegram_user_id)
    except (TypeError, ValueError):
        telegram_user_id = 0
    if not full_name and telegram_user_id > 0:
        full_name = f"Telegram parent {telegram_user_id}"
    return {
        "full_name": full_name,
        "telegram_username": username,
        "telegram_user_id": telegram_user_id if telegram_user_id > 0 else None,
    }


def _connect_parent_from_code(code, user):
    payload = load_parent_invite_code_payload(code)
    if not payload:
        return None
    try:
        student_row_id = int(payload.get("student_row_id") or 0)
    except (TypeError, ValueError):
        student_row_id = 0
    if student_row_id <= 0:
        return None
    profile = _telegram_parent_profile(user)
    if not profile["telegram_user_id"]:
        return None
    return link_parent_via_invite(
        student_row_id,
        full_name=profile["full_name"],
        phone="",
        telegram_username=profile["telegram_username"],
        telegram_user_id=profile["telegram_user_id"],
    )


async def _send_start_payload(message):
    payload = _start_payload(message)
    if payload.startswith("parent_"):
        code = payload.removeprefix("parent_").strip()
        if code:
            parent = None
            try:
                parent = _connect_parent_from_code(code, message.from_user)
            except Exception:
                parent = None

            if parent:
                await message.answer(
                    "👋 <b>Welcome!</b>\n\n"
                    "Your Telegram account is connected to your child's dashboard. "
                    "Open the mini app below.",
                    reply_markup=parent_invite_keyboard(settings.mini_app_url),
                )
                return

            await message.answer(
                "👋 <b>Welcome!</b>\n\n"
                "Parent link received. Open the mini app below to connect to your child's dashboard.",
                reply_markup=parent_invite_keyboard(_parent_invite_url(code)),
            )
            return

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
