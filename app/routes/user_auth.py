from flask import current_app, redirect, request, session, url_for

from app.web.render import render_admin_redirect
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.auth.forms import LoginForm
from app.routes.students.services.auth_service import (
    detect_login_role,
    get_student_by_telegram_user_id,
    get_teacher_by_id,
    link_student_telegram_user,
    verify_admin_credentials,
    verify_student_credentials,
)
from app.routes.students.services.session_state_service import (
    build_dashboard_url,
    current_auth_role,
    current_student_sheet_id,
    logout_portal_session,
    parse_telegram_user_id,
    set_admin_session,
    set_student_session,
    try_auto_login_student_by_telegram,
)

_ADMIN_HANDOFF_SALT = "admin-website-handoff"
_ADMIN_HANDOFF_MAX_AGE_SECONDS = 180


def _admin_handoff_serializer():
    return URLSafeTimedSerializer(
        str(current_app.config.get("SECRET_KEY", "") or ""),
        salt=_ADMIN_HANDOFF_SALT,
    )


def _normalize_admin_handoff_payload(admin):
    if not isinstance(admin, dict):
        return None

    try:
        admin_id = int(admin["id"])
    except (KeyError, TypeError, ValueError):
        return None
    if admin_id <= 0:
        return None

    return {
        "id": admin_id,
        "login": str(admin.get("login", "")).strip(),
        "role": str(admin.get("role", "admin")).strip() or "admin",
        "is_owner": bool(admin.get("is_owner")),
    }


def _current_admin_session_payload():
    try:
        admin_id = int(session.get("admin_id"))
    except (TypeError, ValueError):
        return None
    if admin_id <= 0:
        return None

    return {
        "id": admin_id,
        "login": str(session.get("auth_login", "")).strip(),
        "role": "admin",
        "is_owner": bool(session.get("admin_is_owner")),
    }


def _build_admin_handoff_url(admin):
    normalized_admin = _normalize_admin_handoff_payload(admin)
    if not normalized_admin:
        return ""

    handoff_token = _admin_handoff_serializer().dumps(normalized_admin)
    return url_for("student.admin_continue", handoff=handoff_token, _external=True)


def _load_admin_handoff_payload(raw_token):
    token = str(raw_token or "").strip()
    if not token:
        return None, "Admin website handoff is missing. Please sign in again."

    try:
        payload = _admin_handoff_serializer().loads(
            token,
            max_age=_ADMIN_HANDOFF_MAX_AGE_SECONDS,
        )
    except SignatureExpired:
        return None, "Admin website handoff expired. Please sign in again."
    except BadSignature:
        return None, "Invalid admin website handoff. Please sign in again."

    normalized_payload = _normalize_admin_handoff_payload(payload)
    if not normalized_payload:
        return None, "Admin website handoff is invalid. Please sign in again."
    return normalized_payload, ""


def register_user_auth_routes(
    students,
    *,
    render_login_page,
    render_admin_page,
):
    def render_admin_redirect_page(redirect_url):
        return render_admin_redirect(redirect_url)

    @students.get("/admin")
    def admin_entry():
        if current_auth_role() == "admin":
            return redirect(url_for("student.home", panel="overview", school="all"))
        if current_auth_role() == "student":
            return redirect(url_for("student.home"))
        return render_login_page()

    @students.get("/admin/continue")
    def admin_continue():
        admin_payload, handoff_error = _load_admin_handoff_payload(
            request.args.get("handoff")
        )
        if not admin_payload:
            return render_login_page(auth_error=handoff_error), 401

        if not set_admin_session(admin_payload):
            return render_login_page(
                auth_error="Unable to initialize admin session. Please sign in again.",
            ), 500

        return redirect(url_for("student.home", panel="overview", school="all"))

    @students.get("/")
    def home():
        role = current_auth_role()

        if role == "admin":
            panel_arg = str(request.args.get("panel", "")).strip().lower()
            school_arg = str(request.args.get("school", "")).strip().lower()
            saved_panel = str(session.get("admin_last_panel", "overview")).strip().lower()
            saved_school = str(session.get("admin_last_school", "all")).strip().lower()

            panel = panel_arg or saved_panel or "overview"
            school_filter = school_arg or saved_school or "all"
            edit_teacher_id = request.args.get("edit_teacher_id", "").strip()
            selected_teacher_edit = None
            if panel == "teachers" and edit_teacher_id:
                try:
                    parsed_teacher_id = int(edit_teacher_id)
                except ValueError:
                    parsed_teacher_id = 0
                if parsed_teacher_id > 0:
                    selected_teacher_edit = get_teacher_by_id(parsed_teacher_id)
            return render_admin_page(
                admin_panel=panel,
                admin_teacher_edit=selected_teacher_edit,
                admin_school=school_filter,
            )

        if role == "student":
            own_sheet_student_id = current_student_sheet_id()
            if own_sheet_student_id is None:
                session.clear()
                return render_login_page(
                    auth_error="Student session is invalid. Please login again.",
                ), 401
            return redirect(build_dashboard_url(own_sheet_student_id))

        auto_login_allowed = request.args.get("logged_out", "").strip() != "1"
        telegram_user_id = parse_telegram_user_id(request.args.get("tg_user_id"))
        if (
            auto_login_allowed
            and telegram_user_id
            and try_auto_login_student_by_telegram(
                telegram_user_id,
                get_student_by_telegram_user_id,
            )
        ):
            own_sheet_student_id = current_student_sheet_id()
            if own_sheet_student_id is not None:
                return redirect(build_dashboard_url(own_sheet_student_id))

        return render_login_page()

    @students.post("/login")
    def login():
        login_form = LoginForm()
        login_value = str(login_form.login.data or "").strip()
        if not login_form.validate_on_submit():
            if login_form.csrf_token.errors:
                error_message = (
                    "Form security token is missing or invalid. Please refresh and try again."
                )
            else:
                error_message = "Please enter both login and password."
            return render_login_page(
                auth_error=error_message,
                auth_login_input=login_value,
            ), 400

        password_value = str(login_form.password.data or "")
        role_hint = detect_login_role(login_value)
        if not role_hint:
            return render_login_page(
                auth_error="Login must be admin, Staff#####, MSI#####, or MSIS#####.",
                auth_login_input=login_value,
            ), 400

        if role_hint == "admin":
            admin = verify_admin_credentials(login_value, password_value)
            if not admin:
                return render_login_page(
                    auth_error="Invalid admin credentials.",
                    auth_login_input=login_value,
                ), 401

            set_admin_session(admin)
            session["admin_last_panel"] = "overview"
            session["admin_last_school"] = "all"
            return redirect(url_for("student.home", panel="overview", school="all"))

        student = verify_student_credentials(login_value, password_value)
        if not student:
            return render_login_page(
                auth_error="Invalid student credentials.",
                auth_login_input=login_value,
            ), 401

        telegram_user_id = parse_telegram_user_id(login_form.telegram_user_id.data)
        if telegram_user_id is not None:
            linked = link_student_telegram_user(
                int(student["id"]),
                telegram_user_id,
            )
            if not linked:
                return render_login_page(
                    auth_error="Unable to link Telegram account. Please try again from Telegram.",
                    auth_login_input=login_value,
                ), 500

        if not set_student_session(student, telegram_user_id):
            return render_login_page(
                auth_error="Unable to initialize student session.",
                auth_login_input=login_value,
            ), 500
        return redirect(
            build_dashboard_url(
                student["sheet_student_id"],
                school=student.get("school_code", ""),
            )
        )

    @students.post("/logout")
    def logout():
        logout_portal_session()
        return redirect(url_for("student.home", logged_out=1))
