import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import Response

from backend.application.container import AppContainer
from backend.application.registry import register_application_pages
from backend.application.security_middleware import AuthAndSecurityMiddleware
from backend.core.access.pages import install_guard_handler
from backend.core.access.roles import normalize_role, role_display_name
from backend.core.runtime.config import AppSettings, get_app_settings, get_web_settings
from backend.core.runtime.observability import (
    RequestMetricsMiddleware,
    configure_error_reporting,
    redact_sensitive_path,
)
from backend.core.web.error_pages import internal_server_error_page
from backend.core.web.request_context import RequestContextMiddleware, prime_body_state

_BACKEND_DIR = os.path.dirname(__file__)
_STATIC_DIR = os.path.join(_BACKEND_DIR, "static")
_REACT_DIR = os.path.join(_STATIC_DIR, "react")

LOGGER = logging.getLogger("msi.server")
configure_error_reporting()


def handle_rate_limited(
    request_obj: Request,
    _exc: RateLimitExceeded,
) -> Response:
    message = "Too many attempts. Please wait a moment and try again."
    requested_with = request_obj.headers.get("X-Requested-With", "")
    is_xhr = requested_with == "XMLHttpRequest"
    if request_obj.url.path.startswith("/api/") or is_xhr:
        return JSONResponse({"status": "error", "message": message}, status_code=429)
    return PlainTextResponse(message, status_code=429)


def handle_http_exception(request_obj: Request, exc: HTTPException) -> Response:
    requested_with = request_obj.headers.get("X-Requested-With", "")
    is_xhr = requested_with == "XMLHttpRequest"
    if request_obj.url.path.startswith("/api/") or is_xhr:
        if isinstance(exc.detail, dict):
            return JSONResponse(
                {"status": "error", **exc.detail},
                status_code=exc.status_code,
            )
        return JSONResponse(
            {"status": "error", "message": exc.detail},
            status_code=exc.status_code,
        )
    if exc.status_code in {401, 403}:
        return RedirectResponse(url="/", status_code=302)
    return PlainTextResponse(exc.detail, status_code=exc.status_code)


def handle_unexpected_error(request_obj: Request, exc: Exception) -> Response:
    request_id = str(
        getattr(getattr(request_obj, "state", None), "request_id", "") or ""
    )
    error_summary = " ".join(str(exc).splitlines()).strip()[:500]
    LOGGER.error(
        "Unhandled error request_id=%s method=%s path=%s type=%s detail=%s",
        request_id or "unavailable",
        request_obj.method,
        redact_sensitive_path(request_obj.url.path),
        type(exc).__name__,
        error_summary or "(no detail)",
    )
    requested_with = request_obj.headers.get("X-Requested-With", "")
    is_xhr = requested_with == "XMLHttpRequest"
    if request_obj.url.path.startswith("/api/") or is_xhr:
        return JSONResponse(
            {
                "status": "error",
                "message": "Something went wrong. Please try again.",
                "request_id": request_id,
            },
            status_code=500,
        )
    return internal_server_error_page(request_id)


def unauthorized_page(request_obj: Request) -> Response:
    from backend.core.web.rendering import render_react_page

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


_OPENAPI_TAGS = [
    {"name": "identity", "description": "Authentication and user session management."},
    {"name": "student", "description": "Student-specific views and dashboard APIs."},
    {"name": "parent", "description": "Parent dashboard, student linked data access."},
    {"name": "resources", "description": "Study materials, resources, and file management."},
    {"name": "payments", "description": "Payment history, details, and billing APIs."},
    {"name": "communication", "description": "Chats, system complaints, and messaging routes."},
    {"name": "system", "description": "System diagnostics, health checks, and metadata utilities."},
]


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    try:
        yield
    finally:
        _app.state.container.close()


def _create_base_app(
    app_settings: AppSettings,
    container: AppContainer,
) -> FastAPI:
    app_instance = FastAPI(
        dependencies=[Depends(prime_body_state)],
        title="MSI School API",
        description=(
            "Backend API for MSI School Bot and Web portal management, "
            "serving multiple role-based dashboards."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_tags=_OPENAPI_TAGS,
        lifespan=_lifespan,
    )
    app_instance.state.limiter = container.limiter
    app_instance.state.settings = app_settings
    app_instance.state.container = container
    app_instance.name = "backend.server"
    app_instance.static_folder = _STATIC_DIR
    app_instance.backend_root_path = _BACKEND_DIR

    app_instance.add_middleware(AuthAndSecurityMiddleware)
    app_instance.add_middleware(RequestContextMiddleware)
    app_instance.add_middleware(GZipMiddleware, minimum_size=512)
    app_instance.add_middleware(
        SessionMiddleware,
        secret_key=app_settings.session.secret_key,
        session_cookie=app_settings.session.cookie_name,
        max_age=app_settings.session.max_age_seconds,
        same_site=app_settings.session.same_site,
        https_only=app_settings.session.https_only,
    )
    app_instance.add_middleware(RequestMetricsMiddleware)
    app_instance.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

    install_guard_handler(app_instance)
    app_instance.add_exception_handler(RateLimitExceeded, handle_rate_limited)
    app_instance.add_exception_handler(HTTPException, handle_http_exception)
    app_instance.add_exception_handler(Exception, handle_unexpected_error)
    app_instance.add_api_route(
        "/unauthorized",
        unauthorized_page,
        methods=["GET"],
        include_in_schema=False,
    )
    return app_instance


# Compatibility export used by the existing process wrappers.
settings = get_web_settings()


def _build_default_asset_version() -> str:
    candidate_paths = [
        os.path.join(_BACKEND_DIR, "core", "assets.py"),
        os.path.join(_BACKEND_DIR, "server.py"),
        os.path.join(_BACKEND_DIR, "core", "rendering.py"),
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


_asset_version_override = settings.asset_version
_ASSET_VERSION = (
    _asset_version_override
    if _asset_version_override and _asset_version_override != "1"
    else _build_default_asset_version()
)


def _bootstrap_app(app_instance: FastAPI) -> FastAPI:
    if bool(getattr(app_instance.state, "msi_bootstrapped", False)):
        return app_instance

    # Set static asset dependencies in the rendering boundary.
    import backend.core.web.rendering as render
    render.ASSET_VERSION = _ASSET_VERSION
    render.STATIC_FOLDER = _STATIC_DIR

    # Set static files dependencies in system.py
    import backend.application.system_page as system_routes
    system_routes.STATIC_FOLDER = _STATIC_DIR

    # Include system router
    from backend.application.system_page import router as system_router
    app_instance.include_router(system_router)

    # Include JSON/action API router before page routes.
    from backend.application.api import router as api_v1_router
    app_instance.include_router(api_v1_router)

    register_application_pages(app_instance)

    app_instance.state.msi_bootstrapped = True
    return app_instance


def create_app(
    settings: AppSettings | None = None,
    container: AppContainer | None = None,
) -> FastAPI:
    """Create an isolated application instance for web, tests, or tooling."""

    app_settings = settings or (container.settings if container else get_app_settings())
    app_container = container or AppContainer.build(app_settings)
    return _bootstrap_app(_create_base_app(app_settings, app_container))


app = create_app()
