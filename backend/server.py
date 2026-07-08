import os
import re

from fastapi import FastAPI, Request
from starlette.exceptions import HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.sessions import SessionMiddleware
from slowapi.errors import RateLimitExceeded
from backend.utils.limiter import limiter

from fastapi import Depends
from backend.utils.context import RequestContextMiddleware, prime_body_state
from backend.utils.demo_auth import is_demo_auth_enabled, maybe_apply_demo_auth
from backend.utils.guards import install_guard_handler
from backend.security.roles import is_valid_role, normalize_role, role_display_name
from backend.core.config import get_web_settings
from backend.domains.academics.rating_service import clear_group_cache
from backend.roles.admin.routes import register_admin_page_routes
from backend.pages.academic_director import register_academic_director_page_routes
from backend.pages.ceo import register_ceo_page_routes
from backend.pages.customer_support import register_customer_support_page_routes
from backend.pages.head_of_department import register_head_of_department_page_routes
from backend.pages.hr_manager import register_hr_manager_page_routes
from backend.roles.parent.routes import register_parent_invite_routes
from backend.roles.parent.routes import register_parent_page_routes
from backend.roles.student.routes import register_student_page_routes
from backend.pages.teacher import register_teacher_page_routes

_BACKEND_DIR = os.path.dirname(__file__)
_STATIC_DIR = os.path.join(_BACKEND_DIR, "static")
_REACT_DIR = os.path.join(_STATIC_DIR, "react")

_CACHE_NO_STORE = "no-store, max-age=0"
_CACHE_NO_CACHE_REVALIDATE = "no-cache, no-store, must-revalidate"
_CACHE_LONG_IMMUTABLE = "public, max-age=31536000, immutable"
_CACHE_STATIC_DEFAULT = "public, max-age=2592000, immutable"

_HASHED_REACT_ASSET_FILE_RE = re.compile(r"-[A-Za-z0-9_-]{8,}\.(js|css)$")
_VERSIONED_REACT_ENTRY_RE = re.compile(r"^/static/react/app\.(js|css)$")
_VERSIONED_BUNDLE_RE = re.compile(r"^/static/js/bundles/[^/]+\.js$")

def _resolve_cache_control_header(request_path: str, query_version: str = ""):
    if request_path == "/" or request_path.startswith("/dashboard/"):
        return _CACHE_NO_STORE

    role_page_prefixes = (
        "/academic-director",
        "/academic_director",
        "/admin",
        "/ceo",
        "/hr",
        "/support",
        "/teacher",
        "/parent",
        "/student",
        "/head-of-department",
    )
    if request_path in role_page_prefixes or request_path.startswith(
        tuple(f"{prefix}/" for prefix in role_page_prefixes)
    ):
        return _CACHE_NO_STORE

    if request_path.startswith("/api/"):
        return _CACHE_NO_STORE

    if request_path.startswith("/static/react/"):
        file_name = os.path.basename(request_path)
        if file_name in {"manifest.json", "index.html"}:
            return _CACHE_NO_CACHE_REVALIDATE
        if _HASHED_REACT_ASSET_FILE_RE.search(file_name):
            return _CACHE_LONG_IMMUTABLE
        if query_version and _VERSIONED_REACT_ENTRY_RE.match(request_path):
            return _CACHE_LONG_IMMUTABLE
        return _CACHE_NO_STORE

    if request_path.startswith("/static/js/bundles/"):
        if query_version and _VERSIONED_BUNDLE_RE.match(request_path):
            return _CACHE_LONG_IMMUTABLE
        return _CACHE_NO_STORE

    if request_path.startswith("/static/"):
        return _CACHE_STATIC_DEFAULT

    return None

PUBLIC_PATHS = {
    "/",
    "/login",
    "/auth/telegram",
    # Signed handoff token, not ambient-cookie auth.
    "/admin/continue",
    "/unauthorized",
    "/manifest.webmanifest",
    "/sw.js",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/system/status",
}
_STATE_CHANGING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
# Endpoints authenticated by a signed payload rather than the ambient session
# cookie are exempt from the same-origin/CSRF check: a cross-site forgery gains
# nothing because the request must itself carry a server-verified signature.
# /auth/telegram only trusts HMAC-validated Telegram initData.
_SAME_ORIGIN_EXEMPT_PATHS = {"/auth/telegram"}

class AuthAndSecurityMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_obj = Request(scope, receive=receive)
        path = request_obj.url.path
        maybe_apply_demo_auth(request_obj)

        # 1. Reject cross-origin state changes (Same-Origin check). Applies to
        # every mutating method on every path (not just /api/), so plain admin
        # form posts like /admin/teachers are covered too.
        if request_obj.method in _STATE_CHANGING_METHODS and path not in _SAME_ORIGIN_EXEMPT_PATHS:
            origin = request_obj.headers.get("Origin") or request_obj.headers.get("Referer") or ""
            is_api = path.startswith("/api/")
            if origin:
                from urllib.parse import urlparse
                host = request_obj.headers.get("host") or ""
                host_name = host.split(":")[0] if ":" in host else host
                origin_netloc = urlparse(origin).netloc
                origin_name = origin_netloc.split(":")[0] if ":" in origin_netloc else origin_netloc
                if origin_name != host_name:
                    response = JSONResponse({"status": "error", "message": "Cross-origin request rejected."}, status_code=403)
                    await response(scope, receive, send)
                    return
            elif is_api:
                # No Origin/Referer on an XHR/JSON API call: require the
                # XMLHttpRequest marker, which a cross-site page cannot set
                # without a CORS preflight. Same-origin HTML form posts that omit
                # both headers are allowed here because the SameSite=Lax session
                # cookie already prevents a cross-site POST from carrying auth.
                if request_obj.headers.get("X-Requested-With") != "XMLHttpRequest":
                    response = JSONResponse({"status": "error", "message": "Cross-origin request rejected."}, status_code=403)
                    await response(scope, receive, send)
                    return

        # 2. Authentication check
        is_public = (
            path in PUBLIC_PATHS
            or path.startswith("/static/")
            # Parent invite links are reached by a logged-out parent. Auth is the
            # signed, server-verified token in the URL itself (same trust model as
            # /auth/telegram), so the path must bypass the session-cookie gate.
            or path.startswith("/parent/link/")
            or path.startswith("/parent/invite/")
        )

        if not is_public:
            raw_auth_role = request_obj.session.get("auth_role")
            auth_role = normalize_role(raw_auth_role)
            if not auth_role:
                if raw_auth_role:
                    requested_with = request_obj.headers.get("X-Requested-With") or ""
                    is_xhr = requested_with == "XMLHttpRequest"
                    if path.startswith("/api/") or is_xhr:
                        response = JSONResponse({"status": "error", "message": "Invalid session role."}, status_code=403)
                        await response(scope, receive, send)
                        return
                    response = RedirectResponse(url="/unauthorized", status_code=302)
                    await response(scope, receive, send)
                    return
                requested_with = request_obj.headers.get("X-Requested-With") or ""
                is_xhr = requested_with == "XMLHttpRequest"
                if path.startswith("/api/") or is_xhr:
                    response = JSONResponse({"status": "error", "message": "Authentication required."}, status_code=401)
                    await response(scope, receive, send)
                    return
                response = RedirectResponse(url="/", status_code=302)
                await response(scope, receive, send)
                return
            if not is_valid_role(auth_role):
                requested_with = request_obj.headers.get("X-Requested-With") or ""
                is_xhr = requested_with == "XMLHttpRequest"
                if path.startswith("/api/") or is_xhr:
                    response = JSONResponse({"status": "error", "message": "Invalid session role."}, status_code=403)
                    await response(scope, receive, send)
                    return
                response = RedirectResponse(url="/unauthorized", status_code=302)
                await response(scope, receive, send)
                return

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                header_names = {h[0].lower() for h in headers}

                if b"x-content-type-options" not in header_names:
                    headers.append((b"x-content-type-options", b"nosniff"))
                if b"referrer-policy" not in header_names:
                    headers.append((b"referrer-policy", b"strict-origin-when-cross-origin"))

                cache_control = _resolve_cache_control_header(
                    request_path=path,
                    query_version=request_obj.query_params.get("v", ""),
                )
                if cache_control and b"cache-control" not in header_names:
                    headers.append((b"cache-control", cache_control.encode("utf-8")))

                message["headers"] = headers

            await send(message)

        await self.app(scope, receive, send_wrapper)

# Instantiate FastAPI application
app = FastAPI(
    dependencies=[Depends(prime_body_state)],
    title="MSI School API",
    description="Backend API for MSI School Bot and Web portal management, serving multiple role-based dashboards.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "identity", "description": "Authentication and user session management."},
        {"name": "student", "description": "Student-specific views and dashboard APIs."},
        {"name": "admin", "description": "System administration, settings, and general management."},
        {"name": "parent", "description": "Parent dashboard, student linked data access."},
        {"name": "resources", "description": "Study materials, resources, and file management."},
        {"name": "payments", "description": "Payment history, details, and billing APIs."},
        {"name": "communication", "description": "Chats, system complaints, and messaging routes."},
        {"name": "system", "description": "System diagnostics, health checks, and metadata utilities."},
    ],
)
app.state.limiter = limiter

app.name = "backend.server"
app.static_folder = _STATIC_DIR
app.backend_root_path = _BACKEND_DIR

# Fail closed: a known/default signing key lets anyone forge a session cookie
_secret_key = os.environ.get("APP_SECRET_KEY", os.environ.get("FLASK_SECRET_KEY", "")).strip()
if not _secret_key:
    if os.environ.get("APP_ENV", "").strip().lower() in {"dev", "development", "local"}:
        _secret_key = "dev-only-insecure-key-do-not-use-in-prod"
    else:
        raise RuntimeError(
            "APP_SECRET_KEY must be set. Generate one with: "
            'python -c "import secrets; print(secrets.token_hex(32))"'
        )

# Register Starlette and Custom middlewares
app.add_middleware(AuthAndSecurityMiddleware)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=512)
app.add_middleware(
    SessionMiddleware,
    secret_key=_secret_key,
    session_cookie="session",
    max_age=30 * 24 * 3600,  # 30 days
    same_site=os.environ.get("SESSION_COOKIE_SAMESITE", "lax").lower(),
    https_only=os.environ.get("SESSION_COOKIE_SECURE", "0").strip().lower() not in {"0", "false", "no", "off"},
)

# Mount static files correctly
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

# Expose settings
settings = get_web_settings()

_APP_BOOTSTRAPPED = False


# Role-guard dependencies short-circuit by raising GuardResponse
install_guard_handler(app)


# Rate limiter exception handler
@app.exception_handler(RateLimitExceeded)
def handle_rate_limited(request_obj: Request, exc: RateLimitExceeded):
    message = "Too many attempts. Please wait a moment and try again."
    requested_with = request_obj.headers.get("X-Requested-With", "")
    is_xhr = requested_with == "XMLHttpRequest"
    if request_obj.url.path.startswith("/api/") or is_xhr:
        return JSONResponse({"status": "error", "message": message}, status_code=429)
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(message, status_code=429)


# HTTP exception handler
@app.exception_handler(HTTPException)
def handle_http_exception(request_obj: Request, exc: HTTPException):
    requested_with = request_obj.headers.get("X-Requested-With", "")
    is_xhr = requested_with == "XMLHttpRequest"
    if request_obj.url.path.startswith("/api/") or is_xhr:
        return JSONResponse({"status": "error", "message": exc.detail}, status_code=exc.status_code)
    if exc.status_code in {401, 403}:
        return RedirectResponse(url="/", status_code=302)
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(exc.detail, status_code=exc.status_code)


# Global unexpected error handler
@app.exception_handler(Exception)
def handle_unexpected_error(request_obj: Request, exc: Exception):
    import logging
    logging.exception("Unhandled error on %s %s", request_obj.method, request_obj.url.path)
    requested_with = request_obj.headers.get("X-Requested-With", "")
    is_xhr = requested_with == "XMLHttpRequest"
    if request_obj.url.path.startswith("/api/") or is_xhr:
        return JSONResponse({"status": "error", "message": "Something went wrong. Please try again."}, status_code=500)
    return RedirectResponse(url="/", status_code=302)


@app.get("/unauthorized")
def unauthorized_page(request_obj: Request):
    from backend.render import render_react_page

    auth_role = normalize_role(request_obj.session.get("auth_role"))
    return render_react_page(
        "unauthorized",
        {
            "authRole": auth_role,
            "roleDisplayName": role_display_name(auth_role) if auth_role else "",
            "message": (
                "You are signed in, but this workspace is not available for your role."
                if auth_role
                else "Please sign in with an account that has access to this workspace."
            ),
        },
        title="Unauthorized",
        description="This workspace is not available for your role.",
        status_code=403,
    )


def _build_default_asset_version():
    candidate_paths = [
        os.path.join(_BACKEND_DIR, "js_bundles.py"),
        os.path.join(_BACKEND_DIR, "server.py"),
        os.path.join(_BACKEND_DIR, "render.py"),
        os.path.join(_REACT_DIR, "manifest.json"),
        os.path.join(_REACT_DIR, "app.css"),
        os.path.join(_REACT_DIR, "app.js"),
    ]

    js_roots = [
        os.path.join(_STATIC_DIR, "js"),
    ]
    for js_root in js_roots:
        for root_dir, _dir_names, file_names in os.walk(js_root):
            for file_name in file_names:
                if not file_name.endswith(".js"):
                    continue
                candidate_paths.append(os.path.join(root_dir, file_name))

    if os.path.isdir(_REACT_DIR):
        for root_dir, _dir_names, file_names in os.walk(_REACT_DIR):
            for file_name in file_names:
                if not (file_name.endswith(".js") or file_name.endswith(".css")):
                    continue
                candidate_paths.append(os.path.join(root_dir, file_name))

    mtimes = []
    for path in candidate_paths:
        try:
            mtimes.append(int(os.path.getmtime(path)))
        except OSError:
            continue

    if not mtimes:
        return "1"
    return str(max(mtimes))


_asset_version_override = os.environ.get("ASSET_VERSION", "").strip()
_ASSET_VERSION = (
    _asset_version_override
    if _asset_version_override and _asset_version_override != "1"
    else _build_default_asset_version()
)


def _bootstrap_app(app_instance):
    global _APP_BOOTSTRAPPED
    if _APP_BOOTSTRAPPED:
        return app_instance

    # Loudly flag demo auth at startup. When DEMO_AUTH_ENABLED is on, anyone who
    # reaches the app is auto-logged-in (owner-level for /admin) with no
    # credentials. That is intentional for team testing, but must never be left
    # on for real users — this banner makes it impossible to forget.
    import logging as _logging

    if is_demo_auth_enabled():
        _is_prod = os.environ.get("APP_ENV", "").strip().lower() in {
            "prod",
            "production",
        }
        _logging.getLogger("uvicorn.error").warning(
            "DEMO_AUTH_ENABLED is ON — all visitors are auto-authenticated WITHOUT "
            "a password%s. Set DEMO_AUTH_ENABLED=0 before exposing this to real "
            "users.",
            " (APP_ENV=production!)" if _is_prod else "",
        )

    # Set static files dependencies in render.py
    import backend.render as render
    render.ASSET_VERSION = _ASSET_VERSION
    render.STATIC_FOLDER = _STATIC_DIR

    # Set static files dependencies in system.py
    import backend.routes.system as system_routes
    system_routes.STATIC_FOLDER = _STATIC_DIR

    # Build small legacy Telegram helper bundles at startup. Some deploy
    # environments start from source without generated bundle artifacts, and
    # render_react_page still loads this helper when Telegram support is enabled.
    from backend.js_bundles import ensure_js_bundles
    ensure_js_bundles(_STATIC_DIR)

    # Include system router
    from backend.routes.system import router as system_router
    app_instance.include_router(system_router)

    # Include JSON/action API router before page routes.
    from backend.api.v1.router import router as api_v1_router
    app_instance.include_router(api_v1_router)

    # Register admin and student page routes
    render_admin_page = register_admin_page_routes(
        app_instance,
        clear_group_cache=clear_group_cache,
    )
    register_student_page_routes(app_instance, render_admin_page=render_admin_page)
    register_teacher_page_routes(app_instance)
    register_parent_page_routes(app_instance)
    register_ceo_page_routes(app_instance)
    register_hr_manager_page_routes(app_instance)
    register_customer_support_page_routes(app_instance)
    register_academic_director_page_routes(app_instance)
    register_head_of_department_page_routes(app_instance)
    register_parent_invite_routes(app_instance)

    _APP_BOOTSTRAPPED = True
    return app_instance


def create_app():
    return _bootstrap_app(app)


app = create_app()
