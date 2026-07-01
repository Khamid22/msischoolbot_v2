"""Shared database package — connection, schema, and shared queries."""

from .database import connect_auth_db, get_db_backend
from .cross_queries import *

__all__ = [
    "connect_auth_db",
    "get_db_backend",
]
