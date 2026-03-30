"""Web entry facade for the Flask app instance."""

from app.server import app, settings

__all__ = ["app", "settings"]
