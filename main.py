import errno
import os
import sys

import asyncio
import logging
import threading

from config import get_web_settings
from shared.identity.account_service import init_storage


def _env_positive_int(name, default):
    raw_value = str(os.getenv(name, str(default)) or "").strip()
    try:
        parsed = int(raw_value)
    except ValueError:
        logging.warning("Invalid %s=%r, using %s", name, raw_value, default)
        return int(default)
    return max(parsed, 1)


def _default_worker_threads():
    cpu_count = os.cpu_count() or 1
    return min(max(8, cpu_count * 4), 32)


def _waitress_threads():
    return _env_positive_int("WAITRESS_THREADS", _default_worker_threads())


def _waitress_connection_limit():
    return _env_positive_int("WAITRESS_CONNECTION_LIMIT", 1024)


def _waitress_channel_timeout():
    return _env_positive_int("WAITRESS_CHANNEL_TIMEOUT", 120)


_ADDRESS_IN_USE_ERRNOS = {
    getattr(errno, "EADDRINUSE", 48),
    48,     # macOS / BSD
    98,     # Linux
    10048,  # Windows
}


def _is_wildcard_host(host):
    normalized = str(host or "").strip()
    return normalized in {"0.0.0.0", "*", "::", "[::]"}


def _normalize_listen_target(raw_target, default_port):
    target = str(raw_target or "").strip()
    if not target:
        return ""

    if target.startswith("[") and "]" in target:
        if ":" in target[target.rfind("]") + 1:]:
            return target
        return f"{target}:{default_port}"

    if target.count(":") >= 2:
        return f"[{target}]:{default_port}"

    if ":" in target:
        return target

    return f"{target}:{default_port}"


def _waitress_listen_targets():
    _settings = get_web_settings()
    web_port = int(_settings.flask_port)
    raw_listen = str(os.getenv("WAITRESS_LISTEN", "")).strip()
    if raw_listen:
        targets = []
        for part in raw_listen.replace(",", " ").split():
            normalized = _normalize_listen_target(part, web_port)
            if normalized and normalized not in targets:
                targets.append(normalized)
        if targets:
            return targets

    primary_host = str(_settings.flask_host or "0.0.0.0").strip() or "0.0.0.0"
    targets = [f"{primary_host}:{web_port}"]

    extra_192_host = str(os.getenv("FLASK_HOST_192", "")).strip()
    normalized_extra_192 = _normalize_listen_target(extra_192_host, web_port)
    if (
        normalized_extra_192
        and not _is_wildcard_host(primary_host)
        and normalized_extra_192 not in targets
    ):
        targets.append(normalized_extra_192)

    return targets


def _split_listen_target(raw_target, default_port):
    normalized = str(raw_target or "").strip()
    if not normalized:
        return "", 0

    host = ""
    port_text = str(default_port)
    if normalized.startswith("[") and "]" in normalized:
        bracket_index = normalized.rfind("]")
        host = normalized[1:bracket_index]
        tail = normalized[bracket_index + 1 :]
        if tail.startswith(":"):
            port_text = tail[1:]
    elif ":" in normalized:
        host, port_text = normalized.rsplit(":", 1)
    else:
        host = normalized

    host = str(host or "").strip() or "0.0.0.0"
    try:
        port = int(str(port_text or "").strip())
    except ValueError:
        port = int(default_port)
    if port <= 0:
        port = int(default_port)
    return host, port


def _is_address_in_use_error(exc):
    error_number = getattr(exc, "errno", None)
    if error_number in _ADDRESS_IN_USE_ERRNOS:
        return True
    return "address already in use" in str(exc).strip().lower()


def run_web_server():
    # Production WSGI server: waitress (real threads). Each thread handles one
    # request and one blocking DB call at a time; the bounded psycopg pool
    # (DB_POOL_MAX) caps total DB load. Keep WAITRESS_THREADS ~ DB_POOL_MAX.
    from waitress import serve

    from web.backend.main import app

    listen_targets = _waitress_listen_targets()
    if not listen_targets:
        raise RuntimeError("No valid web server listen targets configured.")

    threads = _waitress_threads()
    connection_limit = _waitress_connection_limit()
    channel_timeout = _waitress_channel_timeout()
    listen = " ".join(listen_targets)

    logging.info(
        "Starting waitress on %s (threads=%s, connection_limit=%s, channel_timeout=%s)",
        listen,
        threads,
        connection_limit,
        channel_timeout,
    )
    try:
        serve(
            app,
            listen=listen,
            threads=threads,
            connection_limit=connection_limit,
            channel_timeout=channel_timeout,
            ident=None,
        )
    except OSError as exc:
        if _is_address_in_use_error(exc):
            logging.error(
                "Cannot start waitress because the listen target is already in use: %s. "
                "Stop the existing process or run with a different PORT/FLASK_PORT.",
                listen,
            )
            raise SystemExit(1) from exc
        raise


async def run_bot():
    from aiogram import Bot, Dispatcher
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode
    from aiogram.types import (
        BotCommand,
        MenuButtonCommands,
    )

    from tgbot.handlers.account_link import router as account_link_router
    from tgbot.handlers.contact_us import router as contact_us_router
    from tgbot.handlers.quick_summary import router as quick_summary_router
    from tgbot.handlers.start import router as start_router
    from tgbot.settings import settings as bot_settings

    bot = Bot(
        token=bot_settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(start_router)
    dp.include_router(account_link_router)
    dp.include_router(quick_summary_router)
    dp.include_router(contact_us_router)
    logging.info(
        "Bot handlers loaded: start=%d account=%d quick=%d contact=%d",
        len(start_router.message.handlers),
        len(account_link_router.message.handlers),
        len(quick_summary_router.callback_query.handlers),
        len(contact_us_router.callback_query.handlers)
        + len(contact_us_router.message.handlers),
    )

    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_chat_menu_button(
        menu_button=MenuButtonCommands(),
    )
    await bot.set_my_commands(
        commands=[
            BotCommand(command="start", description="Open mini app"),
            BotCommand(command="menu", description="Show quick actions"),
            BotCommand(command="whoami", description="Show linked account"),
            BotCommand(command="unlink_me", description="Unlink Telegram account"),
        ]
    )
    await dp.start_polling(bot)


def _resolve_run_mode():
    raw_mode = ""
    if len(sys.argv) > 1:
        raw_mode = str(sys.argv[1] or "").strip().lower()
    if not raw_mode:
        raw_mode = str(os.getenv("RUN_MODE", "both") or "").strip().lower()

    aliases = {
        "both": "both",
        "all": "both",
        "web": "web",
        "server": "web",
        "bot": "bot",
    }
    resolved = aliases.get(raw_mode)
    if resolved:
        return resolved

    logging.warning(
        "Unknown run mode %r. Supported: both, web, bot. Falling back to both.",
        raw_mode,
    )
    return "both"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_storage()

    run_mode = _resolve_run_mode()
    if run_mode == "web":
        run_web_server()
    elif run_mode == "bot":
        asyncio.run(run_bot())
    else:
        logging.info(
            "Running bot + web in one process. "
            "For better concurrency use separate processes: "
            "`python main.py web` and `python main.py bot`."
        )
        flask_thread = threading.Thread(target=run_web_server, daemon=True)
        flask_thread.start()
        asyncio.run(run_bot())
