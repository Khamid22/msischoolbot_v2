import os

from fastapi import Request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from web.backend.render import render_admin_redirect
from web.backend.utils.telegram_auth import telegram_user_id_from_init_data
from shared.identity.account_service import (
    detect_login_role,
    get_student_by_telegram_user_id,
    get_teacher_by_id,
    link_student_telegram_user,
    verify_admin_credentials,
    verify_student_credentials,
)
from web.backend.utils.session import (
    build_dashboard_url,
    current_admin_role,
    current_auth_role,
    current_student_enrollment_id,
    logout_portal_session,
    set_admin_session,
    set_student_session,
    url_for,
)
from web.backend.utils.context import request as request_proxy, session
from web.backend.utils.response_helpers import jsonify, redirect, abort
from web.backend.utils.limiter import limiter

_ADMIN_HANDOFF_SALT = "admin-website-handoff"
_ADMIN_HANDOFF_MAX_AGE_SECONDS = 180


def _admin_handoff_serializer():
    secret = os.environ.get("APP_SECRET_KEY", os.environ.get("FLASK_SECRET_KEY", "")).strip()
    if not secret:
        if os.environ.get("APP_ENV", "").strip().lower() in {"dev", "development", "local"}:
            secret = "dev-only-insecure-key-do-not-use-in-prod"
        else:
            raise RuntimeError(
                "APP_SECRET_KEY must be set. Generate one with: "
                'python -c "import secrets; print(secrets.token_hex(32))"'
            )
    return URLSafeTimedSerializer(
        secret,
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
    render_parent_page=None,
):
    def render_admin_redirect_page(redirect_url):
        return render_admin_redirect(redirect_url)

    @students.get("/admin")
    def admin_entry():
        if current_auth_role() == "admin":
            if current_admin_role() == "parent":
                return redirect(url_for("student.home"))
            return redirect(url_for("student.home", panel="overview", school="all"))
        if current_auth_role() == "student":
            return redirect(url_for("student.home"))
        return render_login_page()

    @students.get("/admin/continue")
    def admin_continue():
        admin_payload, handoff_error = _load_admin_handoff_payload(
            request_proxy.args.get("handoff")
        )
        if not admin_payload:
            return render_login_page(auth_error=handoff_error), 401

        if not set_admin_session(admin_payload):
            return render_login_page(
                auth_error="Unable to initialize admin session. Please sign in again.",
            ), 500

        if current_admin_role() == "parent":
            return redirect(url_for("student.home"))
        return redirect(url_for("student.home", panel="overview", school="all"))

    @students.get("/")
    def home():
        role = current_auth_role()

        if role == "admin":
            if current_admin_role() == "parent":
                return render_admin_page(admin_mode="parent", admin_panel="overview")

            panel_arg = str(request_proxy.args.get("panel", "")).strip().lower()
            school_arg = str(request_proxy.args.get("school", "")).strip().lower()
            saved_panel = str(session.get("admin_last_panel", "overview")).strip().lower()
            saved_school = str(session.get("admin_last_school", "all")).strip().lower()

            panel = panel_arg or saved_panel or "overview"
            school_filter = school_arg or saved_school or "all"
            edit_teacher_id = request_proxy.args.get("edit_teacher_id", "").strip()
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
            enrollment_id = current_student_enrollment_id()
            if enrollment_id is not None:
                return redirect(build_dashboard_url(enrollment_id))
            return redirect(url_for("student.home"))

        # Telegram auto-login happens via POST /auth/telegram, which verifies the
        # signed initData HMAC. The login page's JS calls it on Mini App startup.
        return render_login_page()

    @students.post("/auth/telegram")
    def telegram_auth():
        init_data = str(request_proxy.form.get("init_data", "") or "").strip()
        if not init_data and request_proxy.is_json:
            json_body = request_proxy.get_json(silent=True) or {}
            init_data = str(json_body.get("init_data", "") or "").strip()

        telegram_user_id = telegram_user_id_from_init_data(init_data)
        if telegram_user_id is None:
            return jsonify({"ok": False, "error": "invalid_init_data"}), 401

        student = get_student_by_telegram_user_id(telegram_user_id)
        if not student:
            # Signature is valid but this Telegram account is not linked yet.
            return jsonify({"ok": True, "linked": False})

        if not set_student_session(student, telegram_user_id):
            return jsonify({"ok": False, "error": "session_init_failed"}), 500

        enrollment_id = student.get("enrollment_id")
        redirect_url = (
            build_dashboard_url(enrollment_id, school=student.get("school_code", ""))
            if enrollment_id
            else url_for("student.home")
        )
        return jsonify({"ok": True, "linked": True, "redirect": redirect_url})

    @students.post("/login")
    @limiter.limit("10 per minute; 50 per hour")
    def login(request: Request):
        login_value = str(request_proxy.form.get("login", "")).strip()
        password_value = str(request_proxy.form.get("password", ""))
        init_data_value = str(request_proxy.form.get("init_data", ""))
        csrf_token_value = str(request_proxy.form.get("csrf_token", ""))

        # Validate CSRF manually
        expected_csrf = session.get("csrf_token", "")
        if not expected_csrf or csrf_token_value != expected_csrf:
            return render_login_page(
                auth_error="Form security token is missing or invalid. Please refresh and try again.",
                auth_login_input=login_value,
            ), 400

        if not login_value:
            return render_login_page(
                auth_error="Please enter both login and password.",
                auth_login_input=login_value,
            ), 400

        role_hint = detect_login_role(login_value)

        if role_hint == "admin":
            admin = verify_admin_credentials(login_value, password_value)
            if not admin:
                return render_login_page(
                    auth_error="Invalid admin credentials.",
                    auth_login_input=login_value,
                ), 401

            set_admin_session(admin)
            return redirect(url_for("student.home", panel="overview", school="all"))

        if role_hint == "student":
            student = verify_student_credentials(login_value, password_value)
            if not student:
                return render_login_page(
                    auth_error="Invalid student credentials.",
                    auth_login_input=login_value,
                ), 401

            # Link the Telegram account only from a verified initData signature, never
            # from a client-supplied raw id (which could be forged to hijack a login).
            telegram_user_id = telegram_user_id_from_init_data(init_data_value)
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
            enrollment_id = student.get("enrollment_id")
            if enrollment_id:
                return redirect(build_dashboard_url(enrollment_id, school=student.get("school_code", "")))
            return redirect(url_for("student.home"))

        # No role prefix matched — try parent credentials (free-form logins).
        admin = verify_admin_credentials(login_value, password_value)
        if admin and str(admin.get("role", "")).strip().lower() == "parent":
            set_admin_session(admin)
            return redirect(url_for("student.home"))

        return render_login_page(
            auth_error="Invalid login or password.",
            auth_login_input=login_value,
        ), 401

    @students.post("/logout")
    def logout():
        logout_portal_session()
        return redirect(url_for("student.home", logged_out=1))
