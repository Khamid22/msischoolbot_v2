import html
import os

from aiogram import F, Router
from aiogram.filters import Command

from app.routes.students.services.auth_service import (
    get_admin_by_telegram_user_id,
    get_student_by_telegram_user_id,
    link_admin_telegram_user,
    unlink_telegram_user_links,
    verify_admin_credentials,
)

router = Router()


def _escape(value):
    return html.escape(str(value or ""))


def _env_flag(name, default=False):
    raw_value = str(os.environ.get(name, "1" if default else "0") or "").strip().casefold()
    return raw_value in {"1", "true", "yes", "on"}


def _parse_allowed_telegram_ids():
    raw_value = str(os.environ.get("TEST_ADMIN_TELEGRAM_IDS", "") or "").strip()
    if not raw_value:
        return set()

    allowed_ids = set()
    for chunk in raw_value.split(","):
        normalized = str(chunk or "").strip()
        if not normalized:
            continue
        try:
            parsed = int(normalized)
        except ValueError:
            continue
        if parsed > 0:
            allowed_ids.add(parsed)
    return allowed_ids


def _can_use_test_admin_login(telegram_user_id):
    if not _env_flag("ENABLE_TEST_ADMIN_LOGIN", default=True):
        return False

    allowed_ids = _parse_allowed_telegram_ids()
    if allowed_ids and telegram_user_id not in allowed_ids:
        return False
    return True


def _link_test_admin_account(telegram_user_id):
    if not isinstance(telegram_user_id, int) or telegram_user_id <= 0:
        return False, "Could not read your Telegram user ID."

    if not _can_use_test_admin_login(telegram_user_id):
        return False, "Test admin login is disabled for this account."

    test_login = str(os.environ.get("TEST_ADMIN_LOGIN", "staff280902") or "").strip()
    test_password = str(
        os.environ.get(
            "TEST_ADMIN_PASSWORD",
            os.environ.get("OWNER_ADMIN_PASSWORD", "Khamid007"),
        )
        or ""
    ).strip()
    if not test_login or not test_password:
        return False, "Test admin credentials are not configured."

    admin = verify_admin_credentials(test_login, test_password)
    if not admin:
        return False, "Could not verify test admin credentials."

    linked = link_admin_telegram_user(int(admin["id"]), telegram_user_id)
    if not linked:
        return False, "Could not link this Telegram account to test admin."

    return True, (
        "✅ Test admin login successful.\n"
        f"Linked as <b>{_escape(test_login)}</b>.\n\n"
        "Send /start to open admin mode."
    )


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


@router.message(Command("whoami"))
async def whoami_handler(message):
    user = message.from_user
    telegram_user_id = getattr(user, "id", None)
    if not isinstance(telegram_user_id, int) or telegram_user_id <= 0:
        await message.answer("Could not read your Telegram user ID.")
        return

    linked_admin = _linked_admin_from_user(user)
    linked_student = _linked_student_from_user(user)

    lines = [f"Telegram ID: <code>{telegram_user_id}</code>"]
    if linked_admin:
        lines.append("")
        lines.append("🛡️ Linked as <b>Admin</b>")
        lines.append(f"Login: <b>{_escape(linked_admin.get('login', ''))}</b>")
        lines.append(f"Role: <b>{_escape(linked_admin.get('role', 'admin'))}</b>")

    if linked_student:
        lines.append("")
        lines.append("🎓 Linked as <b>Student</b>")
        lines.append(
            f"Name: <b>{_escape(linked_student.get('full_name', ''))}</b>"
        )
        lines.append(
            f"Student ID: <b>{_escape(linked_student.get('student_id', ''))}</b>"
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
        f"<b>{_escape(', '.join(unlinked_roles))}</b>\n\n"
        "Use Mini App login to link a different account."
    )


@router.message(Command("admin"))
async def test_admin_login_command_handler(message):
    user = message.from_user
    telegram_user_id = getattr(user, "id", None)
    if not isinstance(telegram_user_id, int) or telegram_user_id <= 0:
        await message.answer("Could not read your Telegram user ID.")
        return

    is_success, response_text = _link_test_admin_account(telegram_user_id)
    await message.answer(response_text)
    if not is_success:
        return


@router.callback_query(F.data == "test_admin_login")
async def test_admin_login_callback_handler(query):
    user = query.from_user
    telegram_user_id = getattr(user, "id", None)
    if not isinstance(telegram_user_id, int) or telegram_user_id <= 0:
        await query.answer("Invalid Telegram account.", show_alert=True)
        return

    is_success, response_text = _link_test_admin_account(telegram_user_id)
    await query.answer()
    await query.message.answer(response_text)
