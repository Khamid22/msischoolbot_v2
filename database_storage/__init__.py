"""Shared database package — connection, schema, and shared queries."""

from .database import connect_auth_db, get_db_backend, get_sqlalchemy_database_uri
from .shared_queries import *

__all__ = [
    "connect_auth_db",
    "get_db_backend",
    "get_sqlalchemy_database_uri",
]
