"""Telegram presentation and delivery for billing enforcement events."""

from __future__ import annotations

import json
from datetime import datetime
from urllib import error as urlerror
from urllib import request

from backend.core.runtime.config import get_app_settings
from backend.core.time import SCHOOL_TIMEZONE
from backend.modules.domains.finance.domain_types import (
    BillingHoldTarget,
    BillingNotificationStage,
)


def _money(amount_minor: int) -> str:
    return f"{amount_minor / 100:,.0f}".replace(",", " ")


def _deadline(value: datetime) -> str:
    return value.astimezone(SCHOOL_TIMEZONE).strftime("%d.%m.%Y %H:%M")


def billing_notification_text(
    *,
    stage: BillingNotificationStage,
    target_type: BillingHoldTarget,
    language: str,
    student_name: str,
    invoice_number: str,
    balance_minor: int,
    currency: str,
    deadline_at: datetime,
) -> str:
    is_russian = language == "ru"
    is_household_student = target_type is BillingHoldTarget.HOUSEHOLD_STUDENT
    deadline = _deadline(deadline_at)
    amount = f"{_money(balance_minor)} {currency}"
    if stage is BillingNotificationStage.RESTORED:
        return (
            "Оплата подтверждена. Ограничение доступа снято."
            if is_russian
            else "To'lov tasdiqlandi. Hisobga qo'yilgan cheklov olib tashlandi."
        )
    if is_household_student:
        if stage is BillingNotificationStage.HELD:
            return (
                "Доступ ограничен из-за неоплаченного счёта семьи. "
                "Обратитесь к родителю или в службу поддержки."
                if is_russian
                else "Oiladagi to'lanmagan hisob sababli kirish cheklandi. "
                "Ota-onangiz yoki qo'llab-quvvatlash xizmatiga murojaat qiling."
            )
        hours = 24 if stage is BillingNotificationStage.TWENTY_FOUR_HOURS else 6
        if stage is BillingNotificationStage.INITIAL:
            hours = 48
        return (
            f"Семейный счёт должен быть оплачен до {deadline}. "
            f"До ограничения доступа осталось {hours} ч."
            if is_russian
            else f"Oilaviy hisob {deadline} gacha to'lanishi kerak. "
            f"Kirish cheklanishiga {hours} soat qoldi."
        )
    if stage is BillingNotificationStage.HELD:
        return (
            f"Доступ переведён в режим «только оплата».\n"
            f"Ученик: {student_name}\n"
            f"Счёт: {invoice_number}\n"
            f"К оплате: {amount}"
            if is_russian
            else f"Kirish faqat to'lov rejimiga o'tkazildi.\n"
            f"O'quvchi: {student_name}\n"
            f"Hisob: {invoice_number}\n"
            f"To'lov: {amount}"
        )
    hours = 24 if stage is BillingNotificationStage.TWENTY_FOUR_HOURS else 6
    if stage is BillingNotificationStage.INITIAL:
        hours = 48
    return (
        f"Необходимо оплатить счёт в течение {hours} ч.\n"
        f"Ученик: {student_name}\n"
        f"Счёт: {invoice_number}\n"
        f"К оплате: {amount}\n"
        f"Срок: {deadline}"
        if is_russian
        else f"Hisob {hours} soat ichida to'lanishi kerak.\n"
        f"O'quvchi: {student_name}\n"
        f"Hisob: {invoice_number}\n"
        f"To'lov: {amount}\n"
        f"Muddat: {deadline}"
    )


def send_billing_telegram_message(
    *,
    telegram_user_id: int,
    text: str,
    target_type: BillingHoldTarget,
    language: str,
) -> None:
    settings = get_app_settings()
    if not settings.telegram.bot_token:
        raise RuntimeError("Telegram bot token is not configured.")
    base_url = (
        settings.telegram.mini_app_url.rstrip("/")
        or settings.payme.callback_base_url.rstrip("/")
    )
    payment_path = (
        "/parent/payments"
        if target_type is BillingHoldTarget.LINKED_PARENT
        else "/student/payments"
    )
    button_label = "Оплатить / Поддержка" if language == "ru" else "To'lash / Yordam"
    payload: dict[str, object] = {
        "chat_id": int(telegram_user_id),
        "text": text,
        "disable_web_page_preview": True,
    }
    if base_url:
        payload["reply_markup"] = {
            "inline_keyboard": [
                [
                    {
                        "text": button_label,
                        "web_app": {"url": f"{base_url}{payment_path}"},
                    }
                ]
            ]
        }
    telegram_request = request.Request(
        (
            "https://api.telegram.org/bot"
            f"{settings.telegram.bot_token}/sendMessage"
        ),
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(
            telegram_request,
            timeout=settings.telegram.api_timeout_seconds,
        ) as response:
            if not 200 <= int(response.status) < 300:
                raise RuntimeError("Telegram rejected the billing notification.")
    except (OSError, urlerror.URLError, urlerror.HTTPError) as exc:
        raise RuntimeError("Telegram billing notification failed.") from exc


__all__ = [
    "billing_notification_text",
    "send_billing_telegram_message",
]
