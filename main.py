import asyncio
import threading

from bot.main import run_bot
from web.app import app, settings


def run_flask() -> None:
    app.run(
        host=settings.flask_host,
        port=settings.flask_port,
        debug=False,
        use_reloader=False,
    )


if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    asyncio.run(run_bot())
