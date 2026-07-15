"""Telegram bot entrypoint contracts for staff Mini App linking."""

from __future__ import annotations

import asyncio
from pathlib import Path

from backend.modules.identity import telegram_linking
from tgbot.portal_router import open_portal
from tgbot.routing import BOT_ROUTERS


class _Message:
    def __init__(self):
        self.answers = []

    async def answer(self, text, **kwargs):
        self.answers.append((text, kwargs))


class _Command:
    args = "link_account"


def test_bot_registry_has_the_portal_start_router():
    assert len(BOT_ROUTERS) == 1
    assert BOT_ROUTERS[0].name == "portal_entry"


def test_link_start_command_returns_a_mini_app_button():
    message = _Message()

    asyncio.run(open_portal(message, _Command()))

    text, kwargs = message.answers[0]
    button = kwargs["reply_markup"].inline_keyboard[0][0]
    assert "Link Telegram" in text
    assert button.text == "Open Mini App"
    assert button.web_app.url.startswith("https://")


def test_staff_link_uses_reliable_bot_start_fallback(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_USERNAME", "testtrade2291bot")
    monkeypatch.setenv("BOT_TOKEN", "123456:test-token")

    payload = telegram_linking._connection_payload(None)

    assert payload["open_telegram_url"] == "https://t.me/testtrade2291bot?start=link_account"
    assert "startapp" not in payload["open_telegram_url"]


def test_bot_runtime_configures_the_persistent_mini_app_menu():
    source = Path("main.py").read_text(encoding="utf-8")

    assert "set_chat_menu_button" in source
    assert 'MenuButtonWebApp(text="Open MSI School"' in source
    assert "set_my_commands" in source
