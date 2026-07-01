from backend.server import create_app, settings

app = create_app()

__all__ = ["app", "settings", "create_app"]
