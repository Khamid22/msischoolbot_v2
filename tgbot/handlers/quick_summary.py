import math

from aiogram import F, Router

from tgbot.helpers import (
    escape,
    linked_admin_from_user,
    linked_student_from_user,
    run_blocking,
)
from backend.domains.academics.performance_summary import get_subject_summaries_for_student

router = Router()


def _round_grade_half_up(value):
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0
    if not math.isfinite(numeric):
        return 0
    return int(math.floor(numeric + 0.5))


@router.callback_query(F.data == "student_quick_summary")
async def quick_summary_callback(query):
    if await linked_admin_from_user(query.from_user):
        await query.answer(
            "This quick summary is available only for student accounts.",
            show_alert=True,
        )
        return

    linked_student = await linked_student_from_user(query.from_user)
    if not linked_student:
        await query.answer(
            "Authentication is only through the mini app. Please sign in there first.",
            show_alert=True,
        )
        return

    await query.answer("Preparing summary...")

    summary_rows, summary_error = await run_blocking(
        get_subject_summaries_for_student,
        full_name=str(linked_student.get("full_name", "")),
    )
    if summary_error:
        await query.message.answer(
            "⚠️ Could not load summary data right now.\n"
            f"{escape(summary_error)}"
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
        lines.append(f"📘 <b>Subject: {escape(subject_name)}</b>")
        lines.append(f"• Student Rating: <b>{escape(rating_text)}</b>")
        lines.append(f"• AAP: <b>{_round_grade_half_up(row.get('aap', 0))}</b>")
        lines.append(f"• AR: <b>{int(row.get('ar', 0))}%</b>")
        lines.append(f"• EP: <b>{int(row.get('ep', 0))}</b>")
        lines.append(f"• Total Coins: <b>{int(row.get('total_coins', 0))}</b>")

    await query.message.answer("\n".join(lines))
