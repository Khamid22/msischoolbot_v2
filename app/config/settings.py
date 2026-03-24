"""Web settings facade."""

import os
import sys

try:
    from config import get_web_settings
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from config import get_web_settings

__all__ = ["get_web_settings"]
