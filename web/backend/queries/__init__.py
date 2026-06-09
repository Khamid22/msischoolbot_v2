"""Web backend queries — also re-exports shared queries for a unified namespace."""

from database_storage import connect_auth_db, get_db_backend, get_sqlalchemy_database_uri
from database_storage.shared_queries import *
from database_storage.tables import *

from .admin_queries import *
from .lesson_catalog_queries import *
from .meta_queries import *
from .resource_queries import *
from .subject_summary_queries import *
from .teacher_queries import *
