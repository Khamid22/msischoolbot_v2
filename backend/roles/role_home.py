from backend.identity.roles import normalize_role, role_display_name
from backend.render import generate_csrf, render_react_page
from backend.utils.session import current_auth_login, current_auth_role


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
    return render_react_page(
        page_name,
        {
            "authLogin": current_auth_login(),
            "authRole": current_auth_role(),
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
