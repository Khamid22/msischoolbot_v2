from backend.core.access.roles import normalize_role, role_display_name
from backend.core.web.rendering import generate_csrf, render_react_page
from backend.core.web.request_context import session


def render_role_home(
    page_name: str,
    role: str,
    *,
    title: str,
    description: str,
    cards: list[dict] | None = None,
    view: str = "overview",
):
    normalized_role = normalize_role(role)
    display_name = role_display_name(normalized_role)
    auth_login = str(session.get("auth_login", "")).strip()
    auth_role = normalize_role(session.get("auth_role", ""))
    return render_react_page(
        page_name,
        {
            "authLogin": auth_login,
            "authRole": auth_role,
            "role": normalized_role,
            "roleDisplayName": display_name,
            "title": title,
            "description": description,
            "cards": cards or [],
            "view": view,
            "csrfToken": generate_csrf(),
        },
        title=f"{display_name} Portal",
        description=description,
    )


__all__ = ["render_role_home"]
