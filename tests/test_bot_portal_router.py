"""Telegram bot entrypoint contracts for staff Mini App linking."""

from __future__ import annotations

import asyncio
from pathlib import Path

import main as runtime
from backend.modules.domains.identity import telegram_linking
from tgbot.portal_router import open_portal
from tgbot.routing import BOT_ROUTERS


class _Message:
    def __init__(self):
        self.answers = []

    async def answer(self, text, **kwargs):
        self.answers.append((text, kwargs))


class _Command:
    args = "link_account"


class _ParentCommand:
    args = "parent_INVITE-code_123"


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


def test_parent_invite_start_command_keeps_the_invite_code_in_the_web_app_button():
    message = _Message()

    asyncio.run(open_portal(message, _ParentCommand()))

    text, kwargs = message.answers[0]
    button = kwargs["reply_markup"].inline_keyboard[0][0]
    assert "parent invitation" in text.lower()
    assert button.text == "Open Parent Mini App"
    assert button.web_app.url.endswith("/parent/invite/INVITE-code_123")


class _Result:
    def __init__(self, acquired):
        self.acquired = acquired

    def fetchone(self):
        return {"acquired": self.acquired}


class _Connection:
    def __init__(self, acquired):
        self.acquired = acquired
        self.statements = []
        self.commits = 0
        self.closed = False

    def execute(self, sql, params):
        self.statements.append((sql, params))
        return _Result(self.acquired)

    def commit(self):
        self.commits += 1

    def close(self):
        self.closed = True


def test_bot_polling_uses_one_database_advisory_lock_per_token(monkeypatch):
    leader = _Connection(True)
    monkeypatch.setattr(
        runtime.polling_repository,
        "connect_auth_db",
        lambda: leader,
    )

    acquired = runtime._try_acquire_bot_polling_lock("secret-token")

    assert acquired is leader
    assert "pg_try_advisory_lock" in leader.statements[0][0]
    assert leader.statements[0][1] == (
        runtime._bot_polling_lock_key("secret-token"),
    )
    assert not leader.closed

    runtime._release_bot_polling_lock(acquired, "secret-token")
    assert "pg_advisory_unlock" in leader.statements[-1][0]
    assert leader.closed


def test_bot_polling_follower_releases_database_connection(monkeypatch):
    follower = _Connection(False)
    monkeypatch.setattr(
        runtime.polling_repository,
        "connect_auth_db",
        lambda: follower,
    )

    assert runtime._try_acquire_bot_polling_lock("secret-token") is None
    assert follower.closed


def test_staff_link_uses_reliable_bot_start_fallback(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_USERNAME", "testtrade2291bot")
    monkeypatch.setenv("BOT_TOKEN", "123456:test-token")

    payload = telegram_linking._connection_payload(None)

    assert payload["open_telegram_url"] == "https://t.me/testtrade2291bot?start=link_account"
    assert "startapp" not in payload["open_telegram_url"]


def test_bot_runtime_configures_the_persistent_mini_app_menu():
    source = Path("main.py").read_text(encoding="utf-8")
    polling_repository_source = Path(
        "backend/platform/telegram/polling_repository.py"
    ).read_text(encoding="utf-8")

    assert "set_chat_menu_button" in source
    assert 'MenuButtonWebApp(text="Open MSI School"' in source
    assert "set_my_commands" in source
    assert "pg_try_advisory_lock" in polling_repository_source
    assert "drop_pending_updates=False" in source
