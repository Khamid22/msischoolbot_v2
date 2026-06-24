"""Regression guard: the Telegram bot routers must import and register.

tgbot/handlers/__init__.py previously used rootless imports
(``from handlers.start import ...``) which raised ModuleNotFoundError the moment
``main.run_bot`` tried to load ALL_ROUTERS. This test keeps the package importable
as ``tgbot.handlers`` and asserts every router is wired.
"""

from aiogram import Router


def test_all_routers_import_and_are_routers():
    from tgbot.handlers import ALL_ROUTERS

    assert len(ALL_ROUTERS) == 4
    assert all(isinstance(router, Router) for router in ALL_ROUTERS)
