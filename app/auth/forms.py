from flask_wtf import FlaskForm # type: ignore
from wtforms import HiddenField, PasswordField, StringField # type: ignore
from wtforms.validators import DataRequired  # type: ignore


class LoginForm(FlaskForm):
    login = StringField("Login", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    telegram_user_id = HiddenField("Telegram User ID")


class StudentPasswordChangeForm(FlaskForm):
    current_password = PasswordField("Current Password", validators=[DataRequired()])
    new_password = PasswordField("New Password", validators=[DataRequired()])
    confirm_password = PasswordField("Confirm Password", validators=[DataRequired()])


__all__ = ["LoginForm", "StudentPasswordChangeForm"]
