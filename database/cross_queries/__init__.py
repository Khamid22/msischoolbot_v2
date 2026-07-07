"""Cross-query compatibility barrel.

Temporary compatibility wrapper. Delete after web imports migrate to domain
query modules and Telegram-only helpers stay in dedicated modules.
"""

from .bot_user_queries import *
from .student_queries import *
