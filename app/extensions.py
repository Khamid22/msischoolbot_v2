from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

db: SQLAlchemy = SQLAlchemy()
login_manager: LoginManager = LoginManager()
csrf: CSRFProtect = CSRFProtect()


def init_extensions(app: Flask) -> None:
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)


__all__ = ["db", "login_manager", "csrf", "init_extensions"]
