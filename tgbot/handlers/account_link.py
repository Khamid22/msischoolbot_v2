from aiogram import Router
from aiogram.filters import Command

from tgbot.helpers import escape, linked_admin_from_user, linked_student_from_user
from shared.identity.account_service import unlink_telegram_user_links

router = Router()


@router.message(Command("whoami"))
async def whoami_handler(message):
    user = message.from_user
    telegram_user_id = getattr(user, "id", None)
    if not isinstance(telegram_user_id, int) or telegram_user_id <= 0:
        await message.answer("Could not read your Telegram user ID.")
        return

    linked_admin = linked_admin_from_user(user)
    linked_student = linked_student_from_user(user)

    lines = [f"Telegram ID: <code>{telegram_user_id}</code>"]
    if linked_admin:
        lines.append("")
        lines.append("🛡️ Linked as <b>Admin</b>")
        lines.append(f"Login: <b>{escape(linked_admin.get('login', ''))}</b>")
        lines.append(f"Role: <b>{escape(linked_admin.get('role', 'admin'))}</b>")

    if linked_student:
        lines.append("")
        lines.append("🎓 Linked as <b>Student</b>")
        lines.append(
            f"Name: <b>{escape(linked_student.get('full_name', ''))}</b>"
        )
        lines.append(
            f"Student ID: <b>{escape(linked_student.get('student_id', ''))}</b>"
        )

    if not linked_admin and not linked_student:
        lines.append("")
        lines.append("No linked admin/student account found for this Telegram ID.")

    await message.answer("\n".join(lines))


@router.message(Command("unlink_me"))
async def unlink_me_handler(message):
    user = message.from_user
    telegram_user_id = getattr(user, "id", None)
    if not isinstance(telegram_user_id, int) or telegram_user_id <= 0:
        await message.answer("Could not read your Telegram user ID.")
        return

    result = unlink_telegram_user_links(telegram_user_id)
    if not result.get("success"):
        await message.answer("Failed to unlink this Telegram account.")
        return

    had_admin_link = bool(result.get("had_admin_link"))
    had_student_link = bool(result.get("had_student_link"))
    if not had_admin_link and not had_student_link:
        await message.answer("No linked account was found. Nothing to unlink.")
        return

    unlinked_roles = []
    if had_admin_link:
        unlinked_roles.append("admin")
    if had_student_link:
        unlinked_roles.append("student")

    await message.answer(
        "✅ Unlinked this Telegram account from: "
        f"<b>{escape(', '.join(unlinked_roles))}</b>\n\n"
        "Use Mini App login to link a different account."
    )
