"""Minimal Telegram entrypoint for opening the MSI Mini App securely."""

from __future__ import annotations

import re
from urllib.parse import quote

from aiogram import Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import Message

from tgbot.keyboards.inline_keyboard import parent_invite_keyboard, registration_keyboard
from tgbot.settings import settings


router = Router(name="portal_entry")
_PARENT_INVITE_CODE = re.compile(r"^[A-Za-z0-9_-]{8,128}$")


def _parent_invite_url(argument: str) -> str:
    raw_argument = str(argument or "").strip()
    if not raw_argument.startswith("parent_"):
        return ""
    invite_code = raw_argument.removeprefix("parent_").strip()
    if not _PARENT_INVITE_CODE.fullmatch(invite_code):
        return ""
    return (
        f"{settings.mini_app_url.rstrip('/')}/parent/invite/"
        f"{quote(invite_code, safe='')}"
    )


@router.message(CommandStart())
async def open_portal(message: Message, command: CommandObject | None = None) -> None:
    argument = str(command.args or "").strip() if command else ""
    parent_invite_url = _parent_invite_url(argument)
    if parent_invite_url:
        await message.answer(
            "Open the parent invitation below to verify your Telegram account "
            "and link the student.",
            reply_markup=parent_invite_keyboard(parent_invite_url),
        )
        return

    linking = argument == "link_account"
    text = (
        "Open the MSI School Portal below, sign in, then press <b>Link Telegram</b> "
        "in your Profile settings."
        if linking
        else "Open the MSI School Portal below."
    )
    await message.answer(
        text,
        reply_markup=registration_keyboard(settings.mini_app_url),
    )


__all__ = ["open_portal", "router"]
