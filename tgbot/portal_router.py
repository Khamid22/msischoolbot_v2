"""Minimal Telegram entrypoint for opening the MSI Mini App securely."""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import Message

from tgbot.keyboards.inline_keyboard import registration_keyboard
from tgbot.settings import settings


router = Router(name="portal_entry")


@router.message(CommandStart())
async def open_portal(message: Message, command: CommandObject | None = None) -> None:
    linking = str(command.args or "").strip() == "link_account" if command else False
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
