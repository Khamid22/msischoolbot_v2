from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse

from backend.core.access.workspace_permissions import has_workspace_permission
from backend.core.access.roles import is_valid_role, normalize_role, role_display_name


class GuardResponse(Exception):
    """Raised by a guard dependency to short-circuit with a prebuilt response."""

    def __init__(self, response):
        super().__init__("guard response")
        self.response = response


def install_guard_handler(app):
    @app.exception_handler(GuardResponse)
    def _handle_guard_response(request: Request, exc: GuardResponse):
        return exc.response


def _wants_json(request: Request) -> bool:
    requested_with = str(request.headers.get("X-Requested-With", "")).strip()
    path = request.url.path
    return (
        requested_with == "XMLHttpRequest"
        or path.startswith("/api/")
    )


def unauthorized_response(
    request: Request,
    *,
    message: str = "You are not authorized to view this page.",
    status_code: int = 403,
):
    if _wants_json(request):
        return JSONResponse({"status": "error", "message": message}, status_code=status_code)

    return HTMLResponse(
        f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Unauthorized</title>
  </head>
  <body style="margin:0;background:#f5f7fb;color:#111827;font-family:system-ui,-apple-system,Segoe UI,sans-serif">
    <main style="min-height:100vh;display:grid;place-items:center;padding:24px">
      <section style="max-width:440px;background:white;border:1px solid #e5e7eb;border-radius:18px;padding:24px;box-shadow:0 18px 44px rgba(15,23,42,.10)">
        <p style="margin:0 0 8px;font-size:12px;font-weight:800;letter-spacing:.12em;text-transform:uppercase;color:#64748b">MSI School</p>
        <h1 style="margin:0;font-size:28px;line-height:1.1">Unauthorized</h1>
        <p style="margin:12px 0 0;color:#475569;line-height:1.55">{message}</p>
        <a href="/" style="display:inline-flex;margin-top:18px;border-radius:10px;background:#172263;color:white;padding:10px 14px;text-decoration:none;font-weight:800;font-size:14px">Return home</a>
      </section>
    </main>
  </body>
</html>""",
        status_code=status_code,
    )


def get_session_role(request: Request) -> str:
    return normalize_role(request.session.get("auth_role"))


def require_auth(request: Request) -> str:
    role = get_session_role(request)
    if not role:
        raise GuardResponse(
            unauthorized_response(
                request,
                message="Authentication required.",
                status_code=401,
            )
        )
    if not is_valid_role(role):
        raise GuardResponse(
            unauthorized_response(
                request,
                message="Your session role is not recognized.",
                status_code=403,
            )
        )
    return role


def require_role(*roles, allow_admin: bool = False):
    allowed_roles = {normalize_role(role) for role in roles if normalize_role(role)}
    if allow_admin:
        allowed_roles.add("admin")

    def _dependency(request: Request):
        role = require_auth(request)
        if role in allowed_roles:
            return role
        allowed_names = ", ".join(role_display_name(role) for role in sorted(allowed_roles))
        raise GuardResponse(
            unauthorized_response(
                request,
                message=f"This page requires {allowed_names} access.",
                status_code=403,
            )
        )

    return _dependency


def require_permission(permission):
    normalized_permission = str(permission or "").strip()

    def _dependency(request: Request):
        role = require_auth(request)
        if has_workspace_permission(role, normalized_permission):
            return role
        raise GuardResponse(
            unauthorized_response(
                request,
                message="You do not have permission to perform this action.",
                status_code=403,
            )
        )

    return _dependency


__all__ = [
    "GuardResponse",
    "get_session_role",
    "install_guard_handler",
    "require_auth",
    "require_permission",
    "require_role",
    "unauthorized_response",
]
