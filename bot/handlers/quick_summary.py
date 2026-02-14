import html

from aiogram import F, Router

from web.auth_store import get_student_by_telegram_user_id
from web.sheets_data import get_school_dataset
from web.subject_summary_store import get_subject_summaries_for_student

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


@router.callback_query(F.data == "student_quick_summary")
async def quick_summary_callback(query):
    linked_student = _linked_student_from_user(query.from_user)
    if not linked_student:
        await query.answer("Please login in the mini app first.", show_alert=True)
        return

    await query.answer("Preparing summary...")

    summary_rows, summary_error = get_subject_summaries_for_student(
        full_name=str(linked_student.get("full_name", "")),
        load_dataset=get_school_dataset,
    )
    if summary_error:
        await query.message.answer(
            "⚠️ Could not load summary data right now.\n"
            f"{_escape(summary_error)}"
        )
        return

    if not summary_rows:
        await query.message.answer("⚠️ No summary data found for your profile yet.")
        return

    lines = ["🟢 <b>Quick Summary</b>"]
    for row in summary_rows:
        subject_name = str(row.get("subject_short", "")).strip() or str(
            row.get("subject_name", "")
        ).strip()
        rating_rank = int(row.get("rating_rank", 0))
        rating_total = int(row.get("rating_total", 0))
        rating_text = (
            f"{rating_rank}/{rating_total}"
            if rating_rank > 0 and rating_total > 0
            else "N/A"
        )

        lines.append("")
        lines.append(f"📘 <b>Subject: {_escape(subject_name)}</b>")
        lines.append(f"• Student Rating: <b>{_escape(rating_text)}</b>")
        lines.append(f"• AAP: <b>{int(row.get('aap', 0))}</b>")
        lines.append(f"• AR: <b>{int(row.get('ar', 0))}%</b>")
        lines.append(f"• EP: <b>{int(row.get('ep', 0))}</b>")
        lines.append(f"• Total Coins: <b>{int(row.get('total_coins', 0))}</b>")

    await query.message.answer("\n".join(lines))
