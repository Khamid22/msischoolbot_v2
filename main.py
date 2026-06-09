import os
import sys


def _resolve_bootstrap_run_mode():
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
    return aliases.get(raw_mode, "both")


def _is_gevent_patch_enabled():
    raw_value = str(os.getenv("GEVENT_MONKEY_PATCH", "1") or "").strip()
    return raw_value.casefold() in {"1", "true", "yes", "on"}


def _bootstrap_gevent_monkey_patch():
    if not _is_gevent_patch_enabled():
        return

    run_mode = _resolve_bootstrap_run_mode()
    # Avoid monkey-patching when bot polling runs in the same process.
    # gevent-patched sockets can interfere with asyncio/aiohttp behaviour.
    if run_mode != "web":
        return

    import gevent.monkey

    gevent.monkey.patch_all(thread=False)


_bootstrap_gevent_monkey_patch()

import asyncio
import logging
import threading

from config import get_web_settings
from web.backend.routes.students.services.auth_service import init_storage


def _env_positive_int(name, default):
    raw_value = str(os.getenv(name, str(default)) or "").strip()
    try:
        parsed = int(raw_value)
    except ValueError:
        logging.warning("Invalid %s=%r, using %s", name, raw_value, default)
        return int(default)
    return max(parsed, 1)


def _default_gevent_workers():
    cpu_count = os.cpu_count() or 1
    return min(max(8, cpu_count * 4), 32)


def _waitress_threads():
    return _env_positive_int("WAITRESS_THREADS", _default_gevent_workers())


def _waitress_connection_limit():
    return _env_positive_int("WAITRESS_CONNECTION_LIMIT", 1024)


def _waitress_channel_timeout():
    return _env_positive_int("WAITRESS_CHANNEL_TIMEOUT", 120)


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


def run_web_server():
    if not _is_gevent_patch_enabled():
        from web.backend.main import app

        listen_targets = _waitress_listen_targets()
        primary_target = listen_targets[0] if listen_targets else ""
        host, port = _split_listen_target(primary_target, int(get_web_settings().flask_port))
        if not host or port <= 0:
            raise RuntimeError("No valid web server listen targets configured.")

        logging.info(
            "Starting Flask development server on %s:%s",
            host,
            port,
        )
        app.run(host=host, port=port, threaded=True, use_reloader=False)
        return

    from gevent.pywsgi import WSGIServer
    from geventwebsocket.handler import WebSocketHandler
    from web.backend.main import app

    threads = _waitress_threads()
    connection_limit = _waitress_connection_limit()
    channel_timeout = _waitress_channel_timeout()
    listen_targets = _waitress_listen_targets()
    logging.info(
        "Starting gevent WebSocket server on %s (workers=%s, backlog=%s, timeout=%s)",
        ", ".join(listen_targets),
        threads,
        connection_limit,
        channel_timeout,
    )
    default_port = int(get_web_settings().flask_port)
    servers = []
    for listen_target in listen_targets:
        host, port = _split_listen_target(listen_target, default_port)
        if not host or port <= 0:
            continue

        server = WSGIServer(
            (host, port),
            app,
            handler_class=WebSocketHandler,
            spawn=threads,
            backlog=connection_limit,
            log=None,
            error_log=None,
        )
        servers.append((listen_target, server))

    if not servers:
        raise RuntimeError("No valid web server listen targets configured.")

    for listen_target, server in servers[1:]:
        thread = threading.Thread(
            target=server.serve_forever,
            daemon=True,
            name=f"web-server-{listen_target}",
        )
        thread.start()

    primary_target, primary_server = servers[0]
    logging.info("Primary web server target: %s", primary_target)
    primary_server.serve_forever()


async def run_bot():
    from aiogram import Bot, Dispatcher
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode
    from aiogram.types import (
        BotCommand,
        MenuButtonCommands,
    )

    from telegram_bot.handlers.account_link import router as account_link_router
    from telegram_bot.handlers.contact_us import router as contact_us_router
    from telegram_bot.handlers.quick_summary import router as quick_summary_router
    from telegram_bot.handlers.start import router as start_router
    from telegram_bot.settings import settings as bot_settings

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
