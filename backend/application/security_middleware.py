"""Application authentication, same-origin, and response-security middleware."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from urllib.parse import urlparse

from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.responses import Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from backend.core.access.roles import is_valid_role, normalize_role
from backend.core.web.cache_policy import resolve_cache_control_header

PUBLIC_PATHS = frozenset(
    {
        "/",
        "/login",
        "/auth/telegram",
        "/unauthorized",
        "/manifest.webmanifest",
        "/sw.js",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/system/status",
        "/health/live",
        "/health/ready",
    }
)
STATE_CHANGING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
# These endpoints authenticate their payload instead of relying on the ambient
# session cookie, so they do not gain anything from a forged cross-site request.
SAME_ORIGIN_EXEMPT_PATHS = frozenset(
    {
        "/auth/telegram",
        "/api/v1/integrations/payme/merchant",
    }
)
PASSWORD_CHANGE_ALLOWED_PATHS = frozenset(
    {
        "/account/security",
        "/logout",
        "/auth/telegram",
        "/login",
    }
)


def _is_api_request(request: Request, path: str) -> bool:
    return path.startswith("/api/") or request.headers.get("X-Requested-With") == "XMLHttpRequest"


def _authentication_rejection(
    request: Request,
    path: str,
    *,
    message: str,
    status_code: int,
    redirect_path: str,
) -> Response:
    if _is_api_request(request, path):
        return JSONResponse(
            {"status": "error", "message": message},
            status_code=status_code,
        )
    return RedirectResponse(url=redirect_path, status_code=302)


def _same_origin_rejection(request: Request, path: str) -> Response | None:
    if request.method not in STATE_CHANGING_METHODS or path in SAME_ORIGIN_EXEMPT_PATHS:
        return None
    origin = request.headers.get("Origin") or request.headers.get("Referer") or ""
    if origin:
        request_host = (request.headers.get("host") or "").split(":", 1)[0]
        origin_host = urlparse(origin).netloc.split(":", 1)[0]
        is_rejected = origin_host != request_host
    else:
        is_rejected = (
            path.startswith("/api/") and request.headers.get("X-Requested-With") != "XMLHttpRequest"
        )
    if not is_rejected:
        return None
    return JSONResponse(
        {"status": "error", "message": "Cross-origin request rejected."},
        status_code=403,
    )


def _is_public_path(path: str) -> bool:
    return (
        path in PUBLIC_PATHS
        or path.startswith("/static/")
        or path.startswith("/parent/invite/")
        or path.startswith("/admissions/")
        or path.startswith("/api/v1/public/admissions/")
        or path == "/api/v1/integrations/payme/merchant"
    )


def _role_rejection(request: Request, path: str) -> Response | None:
    raw_role = request.session.get("auth_role")
    role = normalize_role(raw_role)
    if role and is_valid_role(role):
        return None
    if raw_role:
        return _authentication_rejection(
            request,
            path,
            message="Invalid session role.",
            status_code=403,
            redirect_path="/unauthorized",
        )
    return _authentication_rejection(
        request,
        path,
        message="Authentication required.",
        status_code=401,
        redirect_path="/",
    )


def _account_from_session(request: Request) -> dict | None:
    try:
        account_id = int(request.session.get("account_id") or 0)
        session_version = int(request.session.get("session_version") or 0)
    except (TypeError, ValueError):
        return None
    if account_id <= 0 or session_version <= 0:
        return None
    try:
        from backend.modules.domains.identity.service import get_account_by_id

        account = get_account_by_id(account_id)
    except Exception:
        return None
    canonical_role = normalize_role(
        request.session.get("canonical_role") or request.session.get("account_role")
    )
    account_role = normalize_role(account.get("role")) if account else ""
    if not (
        account
        and account.get("status") == "active"
        and int(account.get("session_version") or 0) == session_version
        and account_role
        and account_role == canonical_role
    ):
        return None
    return account


def _canonical_account_rejection(request: Request, path: str) -> Response | None:
    if not request.session.get("account_id") or path == "/logout":
        return None
    if bool(getattr(request.app.state, "testing", False)):
        return None
    account = _account_from_session(request)
    if account is not None:
        request.session["must_change_password"] = bool(account.get("must_change_password"))
        return None
    request.session.clear()
    if _is_api_request(request, path):
        return JSONResponse(
            {
                "status": "error",
                "message": "Your session expired. Please sign in again.",
                "code": "session_expired",
            },
            status_code=401,
        )
    return RedirectResponse(url="/", status_code=302)


def _password_change_rejection(request: Request, path: str) -> Response | None:
    is_required = bool(
        request.session.get("account_id") and request.session.get("must_change_password")
    )
    is_allowed = (
        path in PASSWORD_CHANGE_ALLOWED_PATHS
        or path.startswith("/api/v1/auth/")
        or path.startswith("/static/")
    )
    if not is_required or is_allowed:
        return None
    if _is_api_request(request, path):
        return JSONResponse(
            {
                "status": "error",
                "message": "Change your initial password to continue.",
                "code": "password_change_required",
            },
            status_code=428,
        )
    return RedirectResponse(url="/account/security", status_code=302)


def _security_send(
    request: Request,
    path: str,
    send: Send,
) -> Callable[[Message], Awaitable[None]]:
    async def send_with_security_headers(message: Message) -> None:
        if message["type"] == "http.response.start":
            headers = list(message.get("headers", []))
            header_names = {name.lower() for name, _value in headers}
            if b"x-content-type-options" not in header_names:
                headers.append((b"x-content-type-options", b"nosniff"))
            if b"referrer-policy" not in header_names:
                headers.append((b"referrer-policy", b"strict-origin-when-cross-origin"))
            cache_control = resolve_cache_control_header(
                request_path=path,
                query_version=request.query_params.get("v", ""),
            )
            if cache_control and b"cache-control" not in header_names:
                headers.append((b"cache-control", cache_control.encode("utf-8")))
            message["headers"] = headers
        await send(message)

    return send_with_security_headers


class AuthAndSecurityMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request = Request(scope, receive=receive)
        path = request.url.path
        rejection = _same_origin_rejection(request, path)
        if rejection is None and not _is_public_path(path):
            rejection = (
                _role_rejection(request, path)
                or _canonical_account_rejection(request, path)
                or _password_change_rejection(request, path)
            )
        if rejection is not None:
            await rejection(scope, receive, send)
            return
        await self.app(scope, receive, _security_send(request, path, send))


__all__ = ["AuthAndSecurityMiddleware"]
