"""Telegram bot router registry.

The legacy handler modules were removed while the new bot architecture is being
rebuilt. Keep the runtime registry explicit so polling can still start without
importing old handler code.
"""

BOT_ROUTERS = ()

__all__ = ["BOT_ROUTERS"]
