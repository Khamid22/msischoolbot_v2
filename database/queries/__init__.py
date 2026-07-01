"""Web backend queries — also re-exports shared queries for a unified namespace."""

from database import connect_auth_db, get_db_backend
from database.cross_queries import *
from database.tables import *

from .admin_queries import *
from .announcement_queries import *
from .complaint_queries import *
from .lesson_catalog_queries import *
from .meta_queries import *
from .parent_account_queries import *
from .parent_queries import *
from .payment_queries import *
from .resource_queries import *
from .subject_summary_queries import *
from .teacher_queries import *
from .office_hours import *
