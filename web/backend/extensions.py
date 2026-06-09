from flask import Flask
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect


class _UnavailableSQLAlchemy:
    def init_app(self, _app):
        return None

    def __getattr__(self, name):
        raise RuntimeError(
            "Flask-SQLAlchemy is not initialized for runtime startup. "
            f"Tried to access db.{name}."
        )


db = _UnavailableSQLAlchemy()
login_manager: LoginManager = LoginManager()
csrf: CSRFProtect = CSRFProtect()


def init_extensions(app: Flask) -> None:
    login_manager.init_app(app)
    csrf.init_app(app)


__all__ = ["db", "login_manager", "csrf", "init_extensions"]
