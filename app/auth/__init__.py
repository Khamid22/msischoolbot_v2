"""Authentication and authorization layer."""

try:
    from ..services.auth_service import *  # noqa: F401,F403
except ImportError:
    from app.services.auth_service import *  # noqa: F401,F403

from .policies import *  # noqa: F401,F403
