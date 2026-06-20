"""Framework-free domain logic shared by the web backend and the Telegram bot.

Modules here may import only the database layer (shared.db) and stdlib /
security primitives — never Flask or aiogram. Both web.backend and tgbot
depend on this package; it depends on neither.
"""
