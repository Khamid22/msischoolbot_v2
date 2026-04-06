from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo


def student_menu_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🟢 Quick Summary", callback_data="student_quick_summary")],
            [InlineKeyboardButton(text="🔵 Contact US", callback_data="student_contact_us")],
        ]
    )


def registration_keyboard(mini_app_url, show_test_admin=False):
    rows = [
        [
            InlineKeyboardButton(
                text="Open Mini App",
                web_app=WebAppInfo(url=mini_app_url),
            )
        ]
    ]
    if show_test_admin:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🛡️ Admin (Test)",
                    callback_data="test_admin_login",
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def contact_targets_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👩‍🏫 Course Leader", callback_data="contact_target_course_leader")],
            [InlineKeyboardButton(text="🏢 Administration", callback_data="contact_target_admin")],
            [InlineKeyboardButton(text="❌ Cancel", callback_data="contact_cancel")],
        ]
    )


def contact_cancel_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data="contact_cancel")]
        ]
    )


def contact_confirm_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Confirm", callback_data="contact_confirm_send")],
            [InlineKeyboardButton(text="❌ Cancel", callback_data="contact_cancel")],
        ]
    )


def reply_to_student_keyboard(reply_url):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="↩️ Reply to Student", url=reply_url)]
        ]
    )
