import os
import json

from fastapi import Request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from backend.render import render_admin_redirect
from backend.utils.telegram_auth import telegram_user_id_from_init_data, verify_telegram_init_data
from backend.identity.parent_invites import load_parent_invite_code_payload
from backend.identity.account_service import (
    detect_login_role,
    get_student_by_telegram_user_id,
    get_teacher_by_id,
    link_student_telegram_user,
    record_student_activity,
    verify_admin_credentials,
    verify_student_credentials,
    verify_teacher_credentials,
)
from backend.roles.parent.services import link_parent_via_invite, parent_from_telegram_user_id
from backend.utils.session import (
    build_dashboard_url,
    current_admin_role,
    current_auth_role,
    current_student_enrollment_id,
    logout_portal_session,
    set_admin_session,
    set_parent_session,
    set_student_session,
    set_teacher_session,
    url_for,
)
from backend.utils.context import request as request_proxy, session
from backend.utils.response_helpers import jsonify, redirect, abort, with_status
from backend.utils.limiter import limiter

_ADMIN_HANDOFF_SALT = "admin-website-handoff"
_ADMIN_HANDOFF_MAX_AGE_SECONDS = 180


def _telegram_auth_context(init_data):
    fields = verify_telegram_init_data(init_data)
    if not fields:
        return None
    try:
        user = json.loads(fields.get("user", ""))
    except (TypeError, ValueError):
        return None
    if not isinstance(user, dict):
        return None
    try:
        telegram_user_id = int(user.get("id"))
    except (TypeError, ValueError):
        return None
    if telegram_user_id <= 0:
        return None

    first_name = str(user.get("first_name") or "").strip()
    last_name = str(user.get("last_name") or "").strip()
    username = str(user.get("username") or "").strip().lstrip("@")
    full_name = " ".join(part for part in (first_name, last_name) if part).strip()
    if not full_name:
        full_name = f"Telegram parent {telegram_user_id}"

    return {
        "telegram_user_id": telegram_user_id,
        "full_name": full_name,
        "telegram_username": username,
        "start_param": str(fields.get("start_param") or "").strip(),
    }


def _link_parent_from_telegram_start_param(telegram_context):
    if not isinstance(telegram_context, dict):
        return None
    start_param = str(telegram_context.get("start_param") or "").strip()
    if not start_param.startswith("parent_"):
        return None

    invite_code = start_param.removeprefix("parent_").strip()
    if not invite_code:
        return None

    payload = load_parent_invite_code_payload(invite_code)
    if not payload:
        return None
    try:
        student_row_id = int(payload.get("student_row_id") or 0)
    except (TypeError, ValueError):
        student_row_id = 0
    if student_row_id <= 0:
        return None

    return link_parent_via_invite(
        student_row_id,
        full_name=str(telegram_context.get("full_name") or "").strip(),
        phone="",
        telegram_username=str(telegram_context.get("telegram_username") or "").strip(),
        telegram_user_id=int(telegram_context["telegram_user_id"]),
    )


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
            return with_status(render_login_page(auth_error=handoff_error), 401)

        if not set_admin_session(admin_payload):
            return with_status(render_login_page(
                auth_error="Unable to initialize admin session. Please sign in again.",
            ), 500)

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
            mode_arg = str(request_proxy.args.get("mode", "")).strip().lower()
            saved_panel = str(session.get("admin_last_panel", "overview")).strip().lower()
            saved_school = str(session.get("admin_last_school", "all")).strip().lower()
            saved_mode = str(session.get("admin_last_mode", "")).strip().lower()

            panel = panel_arg or saved_panel or "overview"
            school_filter = school_arg or saved_school or "all"
            admin_mode = mode_arg or saved_mode
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
                admin_mode=admin_mode,
            )

        if role == "student":
            enrollment_id = current_student_enrollment_id()
            if enrollment_id is not None:
                return redirect(build_dashboard_url(enrollment_id))
            return redirect(url_for("student.home"))

        if role == "teacher":
            return redirect("/teacher")

        if role == "parent":
            return render_parent_page()

        # Telegram auto-login happens via POST /auth/telegram, which verifies the
        # signed initData HMAC. The login page's JS calls it on Mini App startup.
        return render_login_page()

    @students.post("/auth/telegram")
    def telegram_auth():
        init_data = str(request_proxy.form.get("init_data", "") or "").strip()
        if not init_data and request_proxy.is_json:
            json_body = request_proxy.get_json(silent=True) or {}
            init_data = str(json_body.get("init_data", "") or "").strip()

        telegram_context = _telegram_auth_context(init_data)
        if not telegram_context:
            return jsonify({"ok": False, "error": "invalid_init_data"}, status_code=401)
        telegram_user_id = int(telegram_context["telegram_user_id"])

        invite_parent = _link_parent_from_telegram_start_param(telegram_context)
        if invite_parent:
            if not set_parent_session(invite_parent, telegram_user_id):
                return jsonify({"ok": False, "error": "session_init_failed"}, status_code=500)
            return jsonify({"ok": True, "linked": True, "role": "parent", "redirect": "/"})

        student = get_student_by_telegram_user_id(telegram_user_id)
        if not student:
            parent = parent_from_telegram_user_id(telegram_user_id)
            if parent:
                if not set_parent_session(parent, telegram_user_id):
                    return jsonify({"ok": False, "error": "session_init_failed"}, status_code=500)
                return jsonify({"ok": True, "linked": True, "role": "parent", "redirect": "/"})

            # Signature is valid but this Telegram account is not linked yet.
            return jsonify({"ok": True, "linked": False})

        if not set_student_session(student, telegram_user_id):
            return jsonify({"ok": False, "error": "session_init_failed"}, status_code=500)

        # Record the login immediately so "last seen" reflects this session even
        # if a later heartbeat ping is missed.
        record_student_activity(int(student["id"]))

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
            return with_status(render_login_page(
                auth_error="Form security token is missing or invalid. Please refresh and try again.",
                auth_login_input=login_value,
            ), 400)

        if not login_value:
            return with_status(render_login_page(
                auth_error="Please enter both login and password.",
                auth_login_input=login_value,
            ), 400)

        role_hint = detect_login_role(login_value)

        if role_hint == "admin":
            admin = verify_admin_credentials(login_value, password_value)
            if not admin:
                return with_status(render_login_page(
                    auth_error="Invalid admin credentials.",
                    auth_login_input=login_value,
                ), 401)

            set_admin_session(admin)
            return redirect(url_for("student.home", panel="overview", school="all"))

        if role_hint == "student":
            student = verify_student_credentials(login_value, password_value)
            if not student:
                return with_status(render_login_page(
                    auth_error="Invalid student credentials.",
                    auth_login_input=login_value,
                ), 401)

            # Link the Telegram account only from a verified initData signature, never
            # from a client-supplied raw id (which could be forged to hijack a login).
            telegram_user_id = telegram_user_id_from_init_data(init_data_value)
            if telegram_user_id is not None:
                linked = link_student_telegram_user(
                    int(student["id"]),
                    telegram_user_id,
                )
                if not linked:
                    return with_status(render_login_page(
                        auth_error="Unable to link Telegram account. Please try again from Telegram.",
                        auth_login_input=login_value,
                    ), 500)

            if not set_student_session(student, telegram_user_id):
                return with_status(render_login_page(
                    auth_error="Unable to initialize student session.",
                    auth_login_input=login_value,
                ), 500)
            # Record the login immediately so "last seen" reflects this session
            # even if a later heartbeat ping is missed.
            record_student_activity(int(student["id"]))
            enrollment_id = student.get("enrollment_id")
            if enrollment_id:
                return redirect(build_dashboard_url(enrollment_id, school=student.get("school_code", "")))
            return redirect(url_for("student.home"))

        if role_hint == "teacher":
            teacher = verify_teacher_credentials(login_value, password_value)
            if not teacher:
                return with_status(render_login_page(
                    auth_error="Invalid teacher credentials.",
                    auth_login_input=login_value,
                ), 401)

            if not set_teacher_session(teacher):
                return with_status(render_login_page(
                    auth_error="Unable to initialize teacher session.",
                    auth_login_input=login_value,
                ), 500)
            return redirect("/teacher")

        # No role prefix matched — try parent credentials (free-form logins).
        admin = verify_admin_credentials(login_value, password_value)
        if admin and str(admin.get("role", "")).strip().lower() == "parent":
            set_admin_session(admin)
            return redirect(url_for("student.home"))

        return with_status(render_login_page(
            auth_error="Invalid login or password.",
            auth_login_input=login_value,
        ), 401)

    @students.post("/logout")
    def logout():
        logout_portal_session()
        return redirect(url_for("student.home", logged_out=1))
