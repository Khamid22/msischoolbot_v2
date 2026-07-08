"""Web backend query compatibility barrel.

Temporary compatibility wrapper. Delete after active web imports migrate to
domain query modules and ``backend.core.database``.
"""

from database import connect_auth_db, get_db_backend
from database.cross_queries import *
from database.tables import *

from .admin_queries import *
from .lesson_catalog_queries import *
from .meta_queries import *
from .parent_account_queries import *
from .parent_queries import *
from .payment_queries import *
from .teacher_queries import *
