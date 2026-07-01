"""Shared identity plumbing."""

import threading
from datetime import datetime

from database import queries

DB_LOCK = threading.Lock()
SYNC_LOCK = threading.Lock()


def utc_now_iso():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def connect():
    return queries.connect_auth_db()


__all__ = ["DB_LOCK", "SYNC_LOCK", "connect", "utc_now_iso"]

