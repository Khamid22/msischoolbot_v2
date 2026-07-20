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
        "/customer-support",
        "customer-support-home",
        "Customer Support Dashboard",
        "Customer Support",
        "Parents",
        "4",
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
    import backend.workspaces.academic_director.page as academic_director_routes
    import backend.workspaces.ceo.page as ceo_page
    import backend.workspaces.customer_support.page as customer_support_page

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
    _set_session(client, {"auth_role": "student", "auth_login": "student@test"})

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
        ("GET", "/parent"),
        ("GET", "/api/v1/auth/me"),
    ],
)
def test_existing_critical_routes_remain_registered(app, method, path):
    routes = _route_methods(app)

    assert path in routes
    assert method in routes[path]


def test_recruitment_routes_replace_the_removed_legacy_hr_pipeline(app):
    routes = _route_methods(app)

    assert "/hr-manager" in routes
    assert "GET" in routes["/hr-manager"]
    assert "/recruitment/pipeline" in routes
    for path in (
        "/hr",
        "/admin/teacher-candidates",
        "/admin/teacher-candidates/{candidate_id}/status",
        "/admin/teacher-candidates/{candidate_id}/promote",
        "/admin/teacher-candidates/{candidate_id}/events/{event_id}/edit",
        "/admin/teacher-candidates/{candidate_id}/events/{event_id}/delete",
    ):
        assert path not in routes


def test_staff_role_pages_are_owned_by_one_staff_module():
    assert not Path("backend/roles").exists()
    for path in [
        Path("backend/workspaces/ceo/page.py"),
        Path("backend/workspaces/customer_support/page.py"),
        Path("backend/modules/reporting/service.py"),
    ]:
        assert path.is_file()
