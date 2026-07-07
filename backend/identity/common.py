"""Shared identity plumbing."""

import threading
from datetime import datetime

from backend.core.database import connect_auth_db as connect

DB_LOCK = threading.Lock()
SYNC_LOCK = threading.Lock()


def utc_now_iso():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


__all__ = ["DB_LOCK", "SYNC_LOCK", "connect", "utc_now_iso"]
