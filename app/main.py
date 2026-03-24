"""Web entry facade for the Flask app instance."""

try:
    from .server import app, settings
except ImportError:
    from server import app, settings

__all__ = ["app", "settings"]
