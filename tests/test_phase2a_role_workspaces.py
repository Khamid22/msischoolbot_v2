"""Phase 2A role workspace shell and route-guard tests."""

import json
import os
from base64 import b64encode
from pathlib import Path

import pytest
from itsdangerous import TimestampSigner


XHR = {"X-Requested-With": "XMLHttpRequest"}


ROLE_WORKSPACES = [
    (
        "ceo",
        "/ceo",
        "ceo-home",
        "CEO Dashboard",
        "CEO",
        "Schools",
        "2",
    ),
    (
        "academic_director",
        "/academic-director",
        "academic-director-home",
        "Academic Director Dashboard",
        "Academic Director",
        "Groups",
        "8",
    ),
    (
        "customer_support",
        "/support",
        "support-home",
        "Customer Support Dashboard",
        "Customer Support",
        "Parents",
        "4",
    ),
    (
        "hr_manager",
        "/hr",
        "hr-home",
        "HR Manager Dashboard",
        "HR Manager",
        "Teachers",
        "3",
    ),
]


def _session_secret():
    return (
        os.environ.get("APP_SECRET_KEY", os.environ.get("FLASK_SECRET_KEY", "")).strip()
        or "dev-only-insecure-key-do-not-use-in-prod"
    )


def _signed_session(data):
    encoded = b64encode(json.dumps(data).encode("utf-8"))
    return TimestampSigner(_session_secret()).sign(encoded).decode("utf-8")


def _set_session(client, data):
    client.cookies.set("session", _signed_session(data))


def _patch_workspace_cards(monkeypatch):
    import backend.pages.academic_director as academic_director_routes
    import backend.pages.ceo as ceo_page
    import backend.pages.customer_support as customer_support_page
    import backend.pages.hr_manager as hr_manager_page

    monkeypatch.setattr(
        ceo_page,
        "ceo_workspace_cards",
        lambda: [
            {"label": "Schools", "value": "2"},
            {"label": "Students", "value": "177"},
            {"label": "Teachers", "value": "3"},
            {"label": "Subjects", "value": "6"},
        ],
    )
    monkeypatch.setattr(
        academic_director_routes,
        "academic_director_workspace_cards",
        lambda: [
            {"label": "Groups", "value": "8"},
            {"label": "Teachers", "value": "3"},
            {"label": "Subjects", "value": "6"},
            {"label": "Students", "value": "177"},
        ],
    )
    monkeypatch.setattr(
        customer_support_page,
        "customer_support_workspace_cards",
        lambda: [
            {"label": "Parents", "value": "4"},
            {"label": "Students", "value": "177"},
            {"label": "Pending Parents/Invites", "value": "3 / 5"},
            {"label": "Support/Payments", "value": "Placeholder"},
        ],
    )
    monkeypatch.setattr(
        hr_manager_page,
        "hr_manager_workspace_cards",
        lambda: [
            {"label": "Teachers", "value": "3"},
            {"label": "Candidates", "value": "1"},
            {"label": "Teacher Academy", "value": "Placeholder"},
        ],
    )


def _route_methods(app):
    routes = {}

    def walk(route_list):
        for route in route_list:
            if type(route).__name__ == "_IncludedRouter":
                walk(route.original_router.routes)
                continue
            path = getattr(route, "path", None)
            methods = getattr(route, "methods", None)
            if path is not None and methods:
                routes.setdefault(path, set()).update(methods)
            nested = getattr(route, "routes", None)
            if nested:
                walk(nested)

    walk(app.routes)
    return routes


@pytest.mark.parametrize(
    ("role", "path", "page", "title", "role_name", "count_label", "count_value"),
    ROLE_WORKSPACES,
)
def test_role_workspace_shell_loads_for_correct_role(
    client,
    monkeypatch,
    role,
    path,
    page,
    title,
    role_name,
    count_label,
    count_value,
):
    _patch_workspace_cards(monkeypatch)
    _set_session(client, {"auth_role": role, "auth_login": f"{role}@test"})

    response = client.get(path)

    assert response.status_code == 200
    assert f'data-react-page="{page}"' in response.text
    assert title in response.text
    assert role_name in response.text
    assert count_label in response.text
    assert count_value in response.text


@pytest.mark.parametrize(
    ("role", "path", "page", "title", "role_name", "count_label", "count_value"),
    ROLE_WORKSPACES,
)
def test_wrong_role_cannot_access_role_workspace(
    client,
    role,
    path,
    page,
    title,
    role_name,
    count_label,
    count_value,
):
    _set_session(client, {"auth_role": "teacher", "auth_login": "teacher@test"})

    response = client.get(path, headers=XHR)

    assert response.status_code == 403
    assert response.json()["message"] == f"This page requires {role_name} access."


@pytest.mark.parametrize(
    ("role", "path", "page", "title", "role_name", "count_label", "count_value"),
    ROLE_WORKSPACES,
)
def test_unauthenticated_user_cannot_access_role_workspace(
    client,
    role,
    path,
    page,
    title,
    role_name,
    count_label,
    count_value,
):
    response = client.get(path, headers=XHR)

    assert response.status_code == 401
    assert response.json()["message"] == "Authentication required."


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/"),
        ("POST", "/login"),
        ("POST", "/auth/telegram"),
        ("GET", "/admin"),
        ("GET", "/teacher"),
        ("GET", "/parent"),
        ("GET", "/api/v1/auth/me"),
    ],
)
def test_existing_critical_routes_remain_registered(app, method, path):
    routes = _route_methods(app)

    assert path in routes
    assert method in routes[path]


def test_small_role_route_modules_are_deleted_after_page_move():
    for path in [
        Path("backend/roles/ceo/routes.py"),
        Path("backend/roles/hr_manager/routes.py"),
        Path("backend/roles/customer_support/routes.py"),
    ]:
        assert not path.exists()

    assert "backend.pages.ceo" in Path("backend/roles/ceo/__init__.py").read_text()
    assert "backend.pages.hr_manager" in Path("backend/roles/hr_manager/__init__.py").read_text()
    assert "backend.pages.customer_support" in Path("backend/roles/customer_support/__init__.py").read_text()
