from flask_wtf import FlaskForm # type: ignore
from wtforms import HiddenField, PasswordField, StringField # type: ignore
from wtforms.validators import DataRequired  # type: ignore


class LoginForm(FlaskForm):
    login = StringField("Login", validators=[DataRequired()])
    # TEMPORARY DEV: password is optional so admin can log in without one.
    # Restore validators=[DataRequired()] before production (see
    # shared/identity/credentials.py _ADMIN_PASSWORDLESS_LOGIN).
    password = PasswordField("Password")
    init_data = HiddenField("Telegram Init Data")


class StudentPasswordChangeForm(FlaskForm):
    current_password = PasswordField("Current Password", validators=[DataRequired()])
    new_password = PasswordField("New Password", validators=[DataRequired()])
    confirm_password = PasswordField("Confirm Password", validators=[DataRequired()])


__all__ = ["LoginForm", "StudentPasswordChangeForm"]
