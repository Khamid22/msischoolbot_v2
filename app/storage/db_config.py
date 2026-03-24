import os
import sys

try:
    from utils.databaseStorage import connect_auth_db, get_auth_db_path
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from utils.databaseStorage import connect_auth_db, get_auth_db_path

__all__ = ["connect_auth_db", "get_auth_db_path"]
