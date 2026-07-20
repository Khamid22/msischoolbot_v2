from fastapi.responses import JSONResponse
import json

from fastapi import APIRouter, Request

from backend.core.web.rendering import generate_csrf, render_react_page
from backend.platform.telegram.init_data import (
    verify_telegram_init_data,
)
from backend.modules.people.parents.service import (
    claim_parent_invite_code,
)
from backend.modules.people.students.service import record_student_activity
from backend.modules.identity.service import authenticate_account_password
from backend.modules.identity.telegram_auth import authenticate_account_telegram
from backend.core.access.roles import dashboard_path_for_role
from backend.modules.identity.session import (
    build_dashboard_url,
    current_auth_role,
    current_student_enrollment_id,
    dashboard_url_for_current_session,
    logout_portal_session,
    set_account_session,
    url_for,
)
from backend.core.web.request_context import request as request_proxy, session
from backend.core.web.responses import redirect, with_status
from backend.core.runtime.rate_limit import limiter

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

    return claim_parent_invite_code(
        invite_code,
        full_name=str(telegram_context.get("full_name") or "").strip(),
        phone="",
        telegram_username=str(telegram_context.get("telegram_username") or "").strip(),
        telegram_user_id=int(telegram_context["telegram_user_id"]),
    )


def register_portal_routes(app):
    """Register login, logout, account-security, and portal entry routes."""

    portal = APIRouter()

    def render_login_page(auth_error="", auth_login_input=""):
        return render_react_page(
            "login",
            {
                "authError": auth_error,
                "authLoginInput": auth_login_input,
                "submitUrl": url_for("student.login"),
                "csrfToken": generate_csrf(),
            },
            title="MSI School Portal",
            description="Login to continue.",
        )

    def account_redirect_url(auth_result):
        session_payload = auth_result.get("session") if isinstance(auth_result, dict) else {}
        if not isinstance(session_payload, dict):
            return ""
        canonical_role = str(
            session_payload.get("account_role")
            or session_payload.get("canonical_role")
            or session_payload.get("auth_role")
            or ""
        ).strip()

        if bool(session_payload.get("must_change_password")):
            return "/account/security"

        if canonical_role == "student":
            enrollment_id = session_payload.get("student_enrollment_id")
            if enrollment_id:
                return build_dashboard_url(
                    enrollment_id,
                    school=session_payload.get("student_school_code", ""),
                )
            return url_for("student.home")

        return dashboard_path_for_role(canonical_role)

    def account_response_role(auth_result):
        session_payload = auth_result.get("session") if isinstance(auth_result, dict) else {}
        if not isinstance(session_payload, dict):
            return ""
        return str(
            session_payload.get("account_role")
            or session_payload.get("canonical_role")
            or session_payload.get("auth_role")
            or ""
        ).strip()

    def record_account_student_activity(auth_result):
        session_payload = auth_result.get("session") if isinstance(auth_result, dict) else {}
        if not isinstance(session_payload, dict) or session_payload.get("auth_role") != "student":
            return
        try:
            student_db_id = int(session_payload.get("student_db_id"))
        except (TypeError, ValueError):
            student_db_id = 0
        if student_db_id > 0:
            record_student_activity(student_db_id)

    @portal.get("/account/security")
    def account_security_page():
        try:
            account_id = int(session.get("account_id") or 0)
        except (TypeError, ValueError):
            account_id = 0
        if account_id <= 0:
            logout_portal_session()
            return redirect(url_for("student.home"))

        role = str(
            session.get("canonical_role")
            or session.get("account_role")
            or session.get("auth_role")
            or ""
        ).strip()
        destination_url = dashboard_url_for_current_session() or dashboard_path_for_role(role)
        return render_react_page(
            "account-security",
            {
                "login": str(session.get("auth_login") or "").strip(),
                "role": role,
                "mustChangePassword": bool(session.get("must_change_password")),
                "passwordApiUrl": "/api/v1/auth/password",
                "continueUrl": destination_url or "/",
                "logoutUrl": "/logout",
            },
            title="Account Security",
            description="Choose a private password for your MSI Portal account.",
            telegram=True,
        )

    @portal.get("/")
    def home():
        role = current_auth_role()

        if role == "student":
            enrollment_id = current_student_enrollment_id()
            if enrollment_id is not None:
                return redirect(build_dashboard_url(enrollment_id))
            return redirect(url_for("student.home"))

        if role == "parent":
            return redirect(dashboard_path_for_role("parent"))

        if role in {"ceo", "customer_support", "academic_director", "head_of_department", "hr_manager"}:
            return redirect(dashboard_path_for_role(role))

        # Telegram auto-login happens via POST /auth/telegram, which verifies the
        # signed initData HMAC. The login page's JS calls it on Mini App startup.
        return render_login_page()

    @portal.post("/auth/telegram")
    def telegram_auth():
        init_data = str(request_proxy.form.get("init_data", "") or "").strip()
        if not init_data and request_proxy.is_json:
            json_body = request_proxy.get_json(silent=True) or {}
            init_data = str(json_body.get("init_data", "") or "").strip()

        telegram_context = _telegram_auth_context(init_data)
        if not telegram_context:
            return JSONResponse({"ok": False, "error": "invalid_init_data"}, status_code=401)
        telegram_user_id = int(telegram_context["telegram_user_id"])

        invite_parent = _link_parent_from_telegram_start_param(telegram_context)
        if invite_parent:
            if not set_account_session(invite_parent.get("auth_result")):
                return JSONResponse({"ok": False, "error": "session_init_failed"}, status_code=500)
            return JSONResponse({
                "ok": True,
                "linked": True,
                "role": "parent",
                "redirect": dashboard_path_for_role("parent"),
            })

        auth_result = authenticate_account_telegram(telegram_user_id)
        if not auth_result:
            # Signature is valid but this Telegram account is not linked yet.
            return JSONResponse({"ok": True, "linked": False})

        if not set_account_session(auth_result):
            return JSONResponse({"ok": False, "error": "session_init_failed"}, status_code=500)

        record_account_student_activity(auth_result)
        redirect_url = account_redirect_url(auth_result)
        response_role = account_response_role(auth_result)
        return JSONResponse({
            "ok": True,
            "linked": True,
            "role": response_role or current_auth_role(),
            "redirect": redirect_url or dashboard_url_for_current_session() or url_for("student.home"),
        })

    @portal.post("/login")
    @limiter.limit("10 per minute; 50 per hour")
    def login(request: Request):
        login_value = str(request_proxy.form.get("login", "")).strip()
        password_value = str(request_proxy.form.get("password", ""))
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

        auth_result = authenticate_account_password(login_value, password_value)
        if not auth_result:
            return with_status(render_login_page(
                auth_error="Invalid login or password.",
                auth_login_input=login_value,
            ), 401)
        if not set_account_session(auth_result):
            return with_status(render_login_page(
                auth_error="Unable to initialize account session.",
                auth_login_input=login_value,
            ), 500)
        record_account_student_activity(auth_result)
        redirect_url = account_redirect_url(auth_result)
        return redirect(redirect_url or dashboard_url_for_current_session() or url_for("student.home"))

    @portal.post("/logout")
    def logout():
        logout_portal_session()
        return redirect(url_for("student.home", logged_out=1))

    app.include_router(portal)


__all__ = ["register_portal_routes"]
