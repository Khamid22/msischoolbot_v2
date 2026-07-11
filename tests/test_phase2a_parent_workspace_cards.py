"""Phase 2A-3B parent workspace cards."""

import json
import os
from base64 import b64encode

import pytest
from itsdangerous import TimestampSigner

from backend.modules.parent_access.cards import build_parent_workspace_cards


XHR = {"X-Requested-With": "XMLHttpRequest"}


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


def _parent_children():
    return [
        {
            "id": 101,
            "student_row_id": 101,
            "student_full_name": "Example Learner One",
            "student_id": "MSI0001",
            "school_name": "Example School",
            "academic_indicators": [
                {"ar": 80, "program_completion_rate": 60},
                {"ar": 90, "program_completion_rate": 80},
            ],
            "recent_lessons": [],
            "payment_summary": {},
        },
        {
            "id": 102,
            "student_row_id": 102,
            "student_full_name": "Example Learner Two",
            "student_id": "MSI0002",
            "school_name": "Example School",
            "academic_indicators": [
                {"ar": 100, "program_completion_rate": 70},
            ],
            "recent_lessons": [],
            "payment_summary": {},
        },
    ]


def _patch_parent_dependencies(monkeypatch, children):
    import backend.workspaces.parent.page as parent_routes

    if isinstance(children, Exception):
        def raise_children(parent_id):
            raise children

        monkeypatch.setattr(parent_routes, "list_parent_client_children", raise_children)
    else:
        monkeypatch.setattr(parent_routes, "list_parent_client_children", lambda parent_id: children)

    monkeypatch.setattr(parent_routes, "list_parent_children", lambda admin_id: [])
    monkeypatch.setattr(parent_routes, "list_resources", lambda: [])
    monkeypatch.setattr(parent_routes, "list_announcements", lambda: [])


def test_parent_workspace_card_provider_counts_children_and_progress():
    cards = build_parent_workspace_cards(
        parent_id=50,
        children=_parent_children(),
    )

    assert cards == [
        {
            "label": "Linked Children",
            "value": "2",
            "detail": "active child links",
            "tone": "text-slate-900",
        },
        {
            "label": "Progress",
            "value": "70%",
            "detail": "average child progress",
            "tone": "text-blue-600",
        },
        {
            "label": "Payment Status",
            "value": "Placeholder",
            "detail": "payment policy later",
            "tone": "text-amber-700",
        },
        {
            "label": "Support",
            "value": "Placeholder",
            "detail": "Customer Support contact later",
            "tone": "text-emerald-700",
        },
    ]


@pytest.mark.parametrize(
    ("parent_id", "children", "linked_value"),
    [
        (None, _parent_children(), "-"),
        (50, None, "-"),
        (50, [], "0"),
    ],
)
def test_parent_workspace_card_provider_returns_safe_placeholders(parent_id, children, linked_value):
    cards = build_parent_workspace_cards(parent_id=parent_id, children=children)

    assert cards[0]["value"] == linked_value
    assert cards[1]["value"] == "-"
    assert cards[2]["value"] == "Placeholder"
    assert cards[3]["value"] == "Placeholder"


def test_parent_route_loads_for_parent(client, monkeypatch):
    _patch_parent_dependencies(monkeypatch, [])
    _set_session(client, {"auth_role": "parent", "auth_login": "parent@example", "parent_id": 50})

    response = client.get("/parent")

    assert response.status_code == 200
    assert 'data-react-page="parent-home"' in response.text
    assert "Linked Children" in response.text
    assert "parentChildren" in response.text


def test_wrong_role_is_denied_from_parent_workspace(client):
    _set_session(client, {"auth_role": "student", "auth_login": "MSI0001", "student_db_id": 1})

    response = client.get("/parent", headers=XHR)

    assert response.status_code == 403
    assert response.json()["message"] == "This page requires Parent access."


def test_unauthenticated_user_is_denied_from_parent_workspace(client):
    response = client.get("/parent", headers=XHR)

    assert response.status_code == 401
    assert response.json()["message"] == "Authentication required."


def test_parent_route_shows_mocked_linked_children_count(client, monkeypatch):
    _patch_parent_dependencies(monkeypatch, _parent_children())
    _set_session(client, {"auth_role": "parent", "auth_login": "parent@example", "parent_id": 50})

    response = client.get("/parent")

    assert response.status_code == 200
    assert 'data-react-page="parent-home"' in response.text
    assert "Linked Children" in response.text
    assert "Progress" in response.text
    assert "Payment Status" in response.text
    assert "Support" in response.text
    assert "active child links" in response.text
    assert "2" in response.text
    assert "70%" in response.text


def test_parent_route_db_failure_returns_placeholder_cards(client, monkeypatch):
    _patch_parent_dependencies(monkeypatch, RuntimeError("database unavailable"))
    _set_session(client, {"auth_role": "parent", "auth_login": "parent@example", "parent_id": 50})

    response = client.get("/parent")

    assert response.status_code == 200
    assert 'data-react-page="parent-home"' in response.text
    assert "Linked Children" in response.text
    assert "Progress" in response.text
    assert "Payment Status" in response.text
    assert "Placeholder" in response.text


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/"),
        ("POST", "/login"),
        ("POST", "/auth/telegram"),
        ("GET", "/admin"),
        ("GET", "/parent"),
        ("GET", "/api/v1/auth/me"),
    ],
)
def test_existing_critical_routes_remain_registered(app, method, path):
    routes = _route_methods(app)

    assert path in routes
    assert method in routes[path]
