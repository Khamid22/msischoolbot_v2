"""Explicit Telegram bot router registry."""

from tgbot.portal_router import router as portal_router


BOT_ROUTERS = (portal_router,)

__all__ = ["BOT_ROUTERS"]
