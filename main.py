import asyncio
import errno
import hashlib
import logging
import os
import sys
import threading

from backend.core.runtime.config import get_web_settings
from backend.modules.domains.identity.bootstrap import init_storage
from backend.platform.telegram import polling_repository

_ADDRESS_IN_USE_ERRNOS = {
    getattr(errno, "EADDRINUSE", 48),
    48,     # macOS / BSD
    98,     # Linux
    10048,  # Windows
}

_TRUE_ENV_VALUES = {"1", "true", "yes", "on"}
_FALSE_ENV_VALUES = {"0", "false", "no", "off"}


def _env_flag(name, *, default):
    raw_value = str(os.getenv(name, "")).strip().lower()
    if not raw_value:
        return bool(default)
    if raw_value in _TRUE_ENV_VALUES:
        return True
    if raw_value in _FALSE_ENV_VALUES:
        return False
    return bool(default)


def _is_railway_runtime():
    return any(
        str(os.getenv(name, "")).strip()
        for name in (
            "RAILWAY_PROJECT_ID",
            "RAILWAY_ENVIRONMENT_ID",
            "RAILWAY_SERVICE_ID",
        )
    )


def _uvicorn_access_log_enabled():
    """Keep local request logs while avoiding high-volume Railway access logs."""
    return _env_flag("UVICORN_ACCESS_LOG", default=not _is_railway_runtime())


def _bot_polling_lock_key(bot_token):
    digest = hashlib.sha256(str(bot_token or "").encode("utf-8")).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=True)


def _bot_polling_lock_retry_seconds():
    try:
        parsed = float(str(os.getenv("BOT_POLL_LOCK_RETRY_SECONDS", "10") or "").strip())
    except ValueError:
        return 10.0
    return max(1.0, min(parsed, 60.0))


def _try_acquire_bot_polling_lock(bot_token):
    return polling_repository.try_acquire_polling_lock(
        _bot_polling_lock_key(bot_token)
    )


def _release_bot_polling_lock(connection, bot_token):
    if connection is None:
        return
    try:
        polling_repository.release_polling_lock(
            connection,
            _bot_polling_lock_key(bot_token),
        )
    except Exception:
        logging.exception("Unable to release the Telegram polling advisory lock.")


async def _wait_for_bot_polling_lock(bot_token):
    waiting_logged = False
    while True:
        try:
            connection = _try_acquire_bot_polling_lock(bot_token)
        except Exception:
            logging.exception(
                "Unable to check the Telegram polling advisory lock; retrying."
            )
            connection = None
        if connection is not None:
            if waiting_logged:
                logging.info("Telegram polling leadership acquired.")
            return connection
        if not waiting_logged:
            logging.warning(
                "Another application instance owns Telegram polling; waiting for leadership."
            )
            waiting_logged = True
        await asyncio.sleep(_bot_polling_lock_retry_seconds())


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


def _web_listen_targets():
    _settings = get_web_settings()
    web_port = int(_settings.web_port)
    raw_listen = str(os.getenv("WEB_LISTEN", os.getenv("WAITRESS_LISTEN", ""))).strip()
    if raw_listen:
        targets = []
        for part in raw_listen.replace(",", " ").split():
            normalized = _normalize_listen_target(part, web_port)
            if normalized and normalized not in targets:
                targets.append(normalized)
        if targets:
            return targets

    primary_host = str(_settings.web_host or "0.0.0.0").strip() or "0.0.0.0"
    targets = [f"{primary_host}:{web_port}"]

    extra_192_host = str(os.getenv("WEB_HOST_192", os.getenv("FLASK_HOST_192", ""))).strip()
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
    import uvicorn

    from backend.core.runtime.config import get_web_settings

    listen_targets = _web_listen_targets()
    if not listen_targets:
        raise RuntimeError("No valid web server listen targets configured.")

    _settings = get_web_settings()
    web_port = int(_settings.web_port)
    host, port = _split_listen_target(listen_targets[0], web_port)
    access_log_enabled = _uvicorn_access_log_enabled()

    logging.info(
        "Starting uvicorn on %s:%s (1 worker process, access_log=%s)",
        host,
        port,
        access_log_enabled,
    )
    try:
        uvicorn.run(
            "backend.server:app",
            host=host,
            port=port,
            log_level="info",
            access_log=access_log_enabled,
        )
    except OSError as exc:
        if _is_address_in_use_error(exc):
            logging.error(
                "Cannot start uvicorn because the listen target is already in use: %s:%s. "
                "Stop the existing process or run with a different PORT/WEB_PORT.",
                host,
                port,
            )
            raise SystemExit(1) from exc
        raise


async def run_bot():
    from aiogram import Bot, Dispatcher
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode
    from aiogram.types import BotCommand, MenuButtonWebApp, WebAppInfo

    from tgbot.routing import BOT_ROUTERS
    from tgbot.settings import settings as bot_settings

    polling_lock = await _wait_for_bot_polling_lock(bot_settings.bot_token)
    bot = None
    try:
        bot = Bot(
            token=bot_settings.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        dp = Dispatcher()

        bot_routers = tuple(BOT_ROUTERS)
        for router in bot_routers:
            dp.include_router(router)

        try:
            web_app = WebAppInfo(url=bot_settings.mini_app_url)
            await bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(text="Open MSI School", web_app=web_app)
            )
            await bot.set_my_commands(
                [BotCommand(command="start", description="Open MSI School")]
            )
        except Exception:
            logging.exception("Unable to configure the Telegram Mini App menu button.")

        if bot_routers:
            logging.info("Starting Telegram bot polling (%d routers).", len(bot_routers))
        else:
            logging.warning(
                "Starting Telegram bot polling with no registered routers. "
                "The old handler layer was removed; install the new bot routing layer "
                "before expecting commands or callbacks to respond."
            )

        # Preserve queued invite commands across deploys, then long-poll.
        await bot.delete_webhook(drop_pending_updates=False)
        await dp.start_polling(bot)
    finally:
        if bot is not None:
            await bot.session.close()
        _release_bot_polling_lock(polling_lock, bot_settings.bot_token)


def _resolve_run_mode():
    raw_mode = ""
    if len(sys.argv) > 1:
        raw_mode = str(sys.argv[1] or "").strip().lower()
    if not raw_mode:
        raw_mode = str(os.getenv("RUN_MODE", "web") or "").strip().lower()

    aliases = {
        "both": "both",
        "all": "both",
        "web": "web",
        "server": "web",
        "bot": "bot",
        "worker": "worker",
        "recruitment-worker": "worker",
    }
    resolved = aliases.get(raw_mode)
    if resolved:
        return resolved

    logging.warning(
        "Unknown run mode %r. Supported: both, web, bot, worker. Falling back to web.",
        raw_mode,
    )
    return "web"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_storage()

    run_mode = _resolve_run_mode()
    if run_mode == "web":
        run_web_server()
    elif run_mode == "bot":
        asyncio.run(run_bot())
    elif run_mode == "worker":
        from backend.application.worker import run_worker
        from backend.application.worker_health import start_worker_health_server

        health_settings = get_web_settings()
        health_server = start_worker_health_server(
            host=health_settings.web_host,
            port=health_settings.web_port,
        )
        try:
            run_worker()
        finally:
            health_server.close()
    else:
        logging.info(
            "Running bot + web in one process. "
            "For better concurrency use separate processes: "
            "`python main.py web` and `python main.py bot`."
        )
        web_thread = threading.Thread(target=run_web_server, daemon=True)
        web_thread.start()
        try:
            asyncio.run(run_bot())
        except Exception:
            # The web server runs on a daemon thread, so if the bot fails to
            # start (missing/invalid BOT_TOKEN, no network) we must NOT let the
            # main thread exit — that would tear the whole process down and take
            # the web app with it. Log and keep serving web instead.
            logging.exception(
                "Telegram bot stopped; keeping the web server running."
            )
        finally:
            web_thread.join()
