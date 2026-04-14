import threading
from datetime import datetime, timezone

from app.storage import queries

_DB_LOCK = threading.Lock()


def connect_chat_db():
    return queries.connect_auth_db()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fmt_display(iso_str: str) -> str:
    """Return a human-readable timestamp like '10 Apr 2026, 14:32'."""
    try:
        dt = datetime.strptime(iso_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        return dt.strftime("%-d %b %Y, %H:%M")
    except Exception:
        return iso_str
