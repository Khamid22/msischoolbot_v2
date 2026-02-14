import html
import os

from aiogram import F, Router
from aiogram.fsm.state import State, StatesGroup

from bot.keyboards.inline_keyboard import (
    contact_cancel_keyboard,
    contact_confirm_keyboard,
    contact_targets_keyboard,
    reply_to_student_keyboard,
)
from web.auth_store import get_student_by_telegram_user_id

router = Router()

COURSE_LEADER_CHAT = (os.environ.get("COURSE_LEADER_CHAT", "@py_ds") or "@py_ds").strip()
ADMIN_CHAT = (os.environ.get("ADMIN_CHAT", "@msischool_admin") or "@msischool_admin").strip()


class ContactState(StatesGroup):
    waiting_message = State()
    waiting_confirmation = State()


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


def _target_by_key(target_key):
    if target_key == "course_leader":
        return {
            "label": "Course Leader",
            "chat_id": COURSE_LEADER_CHAT,
        }
    if target_key == "admin":
        return {
            "label": "Administration",
            "chat_id": ADMIN_CHAT,
        }
    return None


@router.callback_query(F.data == "student_contact_us")
async def contact_us_callback(query, state):
    linked_student = _linked_student_from_user(query.from_user)
    if not linked_student:
        await query.answer(
            "Authentication is only through the mini app. Please sign in there first.",
            show_alert=True,
        )
        return

    await state.clear()
    await query.answer()
    await query.message.answer(
        "🔵 <b>Contact US</b>\n\nChoose who should receive your message:",
        reply_markup=contact_targets_keyboard(),
    )


@router.callback_query(F.data == "contact_target_course_leader")
async def contact_target_course_leader_callback(query, state):
    linked_student = _linked_student_from_user(query.from_user)
    if not linked_student:
        await query.answer(
            "Authentication is only through the mini app. Please sign in there first.",
            show_alert=True,
        )
        await state.clear()
        return

    await state.set_state(ContactState.waiting_message)
    await state.update_data(contact_target_key="course_leader")
    await query.answer()
    await query.message.answer(
        "✍️ Write your message to <b>Course Leader</b>.\n\n"
        "Send one text message and then confirm.",
        reply_markup=contact_cancel_keyboard(),
    )


@router.callback_query(F.data == "contact_target_admin")
async def contact_target_admin_callback(query, state):
    linked_student = _linked_student_from_user(query.from_user)
    if not linked_student:
        await query.answer(
            "Authentication is only through the mini app. Please sign in there first.",
            show_alert=True,
        )
        await state.clear()
        return

    await state.set_state(ContactState.waiting_message)
    await state.update_data(contact_target_key="admin")
    await query.answer()
    await query.message.answer(
        "✍️ Write your message to <b>Administration</b>.\n\n"
        "Send one text message and then confirm.",
        reply_markup=contact_cancel_keyboard(),
    )


@router.message(ContactState.waiting_message)
async def collect_contact_message(message, state):
    linked_student = _linked_student_from_user(message.from_user)
    if not linked_student:
        await state.clear()
        await message.answer(
            "Authentication is only through the mini app. Please sign in there first."
        )
        return

    message_text = str(message.text or "").strip()
    if not message_text:
        await message.answer("Please send your message as plain text.")
        return

    data = await state.get_data()
    target = _target_by_key(data.get("contact_target_key", ""))
    if not target:
        await state.clear()
        await message.answer("Session expired. Please open Contact US again.")
        return

    await state.update_data(contact_message_text=message_text)
    await state.set_state(ContactState.waiting_confirmation)

    await message.answer(
        "Please confirm sending this message:\n\n"
        f"To: <b>{_escape(target['label'])}</b>\n"
        f"Message:\n{_escape(message_text)}",
        reply_markup=contact_confirm_keyboard(),
    )


@router.callback_query(ContactState.waiting_confirmation, F.data == "contact_confirm_send")
async def confirm_contact_send_callback(query, state):
    data = await state.get_data()
    target = _target_by_key(data.get("contact_target_key", ""))
    message_text = str(data.get("contact_message_text", "")).strip()

    if not target or not message_text:
        await state.clear()
        await query.answer()
        await query.message.answer("Session expired. Please open Contact US again.")
        return

    linked_student = _linked_student_from_user(query.from_user)
    if not linked_student:
        await state.clear()
        await query.answer(
            "Authentication is only through the mini app. Please sign in there first.",
            show_alert=True,
        )
        return

    student_full_name = str(query.from_user.full_name or "").strip()
    student_login = ""
    if linked_student:
        linked_name = str(linked_student.get("full_name", "")).strip()
        if linked_name:
            student_full_name = linked_name
        student_login = str(linked_student.get("student_id", "")).strip()

    username_text = (
        f"@{query.from_user.username}"
        if query.from_user.username
        else "No username"
    )
    reply_url = (
        f"https://t.me/{query.from_user.username}"
        if query.from_user.username
        else f"tg://user?id={query.from_user.id}"
    )

    receiver_text = (
        "📩 <b>New student message</b>\n\n"
        f"From: <b>{_escape(student_full_name)}</b>\n"
        f"Student ID: <b>{_escape(student_login or '-')}</b>\n"
        f"Telegram: <b>{_escape(username_text)}</b>\n"
        f"Telegram ID: <code>{query.from_user.id}</code>\n\n"
        f"Message to {_escape(target['label'])}:\n"
        f"{_escape(message_text)}"
    )

    try:
        await query.bot.send_message(
            chat_id=target["chat_id"],
            text=receiver_text,
            reply_markup=reply_to_student_keyboard(reply_url),
        )
    except Exception:
        await query.answer()
        await query.message.answer(
            "⚠️ Could not deliver your message right now. Please try again later."
        )
        return

    await state.clear()
    await query.answer("Message sent")
    await query.message.answer(
        f"✅ Your message was sent to <b>{_escape(target['label'])}</b>."
    )


@router.callback_query(F.data == "contact_cancel")
async def cancel_contact_callback(query, state):
    await state.clear()
    await query.answer("Cancelled")
    await query.message.answer("❌ Contact request cancelled.")
