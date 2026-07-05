"""Phase 2A-3C System Admin workspace cards."""

import json
import os
from base64 import b64encode

import pytest
from itsdangerous import TimestampSigner

from backend.roles.admin.system_admin_cards import system_admin_workspace_cards


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


class _Rows:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


class _SystemAdminConnection:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def execute(self, sql):
        if "account_telegram_links" in sql:
            return _Rows({"count": 5})
        if "status = 'active'" in sql:
            return _Rows({"count": 181})
        if "status = 'pending'" in sql:
            return _Rows({"count": 3})
        if "FROM msi_v2.accounts" in sql:
            return _Rows({"count": 185})
        raise AssertionError(f"Unexpected SQL: {sql}")


def _minimal_page_context():
    return {
        "panel": "overview",
        "school_filter": "all",
        "sync_errors": [],
        "load_error": "",
        "admin_students": [],
        "admin_teachers": [],
        "admin_teacher_candidates": [],
        "admin_teacher_academy": [],
        "admin_complaints": [],
        "admin_parents": [],
        "admin_parent_children": [],
        "admin_teacher_options": [],
        "admin_group_options": [],
        "admin_teacher_edit": None,
        "admin_teacher_edit_school": "",
        "admin_school_options": [{"code": "all", "label": "All Schools"}],
        "admin_quick_stats": {},
        "admin_school_info": [],
        "admin_subject_info": [],
        "admin_group_zones": {"green": [], "yellow": [], "red": []},
        "admin_resource_types": [],
        "admin_resource_active_types": [],
        "admin_resources": [],
        "admin_resource_subject_options": [],
        "admin_resource_upload_enabled": False,
    }


def _minimal_academic_context():
    return {
        "schools": [],
        "subjects": [],
        "groups": [],
        "enrollments": [],
        "lessons": [],
        "schedules": [],
        "sessions": [],
        "curriculum_programs": [],
        "curriculum_items": [],
        "enrollment_summary": {},
    }


def _patch_admin_page_context(monkeypatch):
    import backend.roles.admin.routes.admin_page as admin_page

    monkeypatch.setattr(
        admin_page,
        "build_admin_page_context",
        lambda **kwargs: _minimal_page_context(),
    )
    monkeypatch.setattr(admin_page, "list_admin_academic_context", _minimal_academic_context)
    monkeypatch.setattr(admin_page, "list_announcements", lambda: [])


def _mock_cards():
    return [
        {"label": "Total Accounts", "value": "185", "detail": "shared login identities"},
        {"label": "Active Accounts", "value": "181", "detail": "usable accounts"},
        {"label": "Pending Accounts", "value": "3", "detail": "waiting for activation/linking"},
        {"label": "Telegram Links", "value": "5", "detail": "active linked accounts"},
        {"label": "Audit / Settings", "value": "Placeholder", "detail": "technical tools later"},
    ]


def test_system_admin_card_provider_counts_accounts(monkeypatch):
    import backend.roles.admin.system_admin_cards as system_cards

    monkeypatch.setattr(system_cards.queries, "connect_auth_db", lambda: _SystemAdminConnection())

    cards = system_admin_workspace_cards()

    assert cards == [
        {
            "label": "Total Accounts",
            "value": "185",
            "detail": "shared login identities",
            "tone": "text-slate-900",
        },
        {
            "label": "Active Accounts",
            "value": "181",
            "detail": "usable accounts",
            "tone": "text-emerald-700",
        },
        {
            "label": "Pending Accounts",
            "value": "3",
            "detail": "waiting for activation/linking",
            "tone": "text-amber-700",
        },
        {
            "label": "Telegram Links",
            "value": "5",
            "detail": "active linked accounts",
            "tone": "text-blue-700",
        },
        {
            "label": "Audit / Settings",
            "value": "Placeholder",
            "detail": "technical tools later",
            "tone": "text-slate-700",
        },
    ]


def test_system_admin_card_provider_returns_placeholders_on_db_failure(monkeypatch):
    import backend.roles.admin.system_admin_cards as system_cards

    def fail_connect():
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(system_cards.queries, "connect_auth_db", fail_connect)

    cards = system_admin_workspace_cards()

    assert cards[0]["value"] == "-"
    assert cards[1]["value"] == "-"
    assert cards[2]["value"] == "-"
    assert cards[3]["value"] == "-"
    assert cards[4]["value"] == "Placeholder"


def test_system_admin_admin_can_access_admin_with_cards(client, monkeypatch):
    import backend.roles.admin.routes.admin_page as admin_page

    _patch_admin_page_context(monkeypatch)
    monkeypatch.setattr(admin_page, "system_admin_workspace_cards", _mock_cards)
    _set_session(
        client,
        {
            "auth_role": "admin",
            "auth_login": "admin",
            "account_role": "system_admin",
            "canonical_role": "system_admin",
            "admin_id": 1,
            "admin_role": "owner",
        },
    )

    response = client.get("/admin")

    assert response.status_code == 200
    assert 'data-react-page="admin-home"' in response.text
    assert "Total Accounts" in response.text
    assert "Active Accounts" in response.text
    assert "Pending Accounts" in response.text
    assert "Telegram Links" in response.text
    assert "Audit / Settings" in response.text
    assert "185" in response.text


def test_wrong_role_is_denied_from_admin(client):
    _set_session(client, {"auth_role": "teacher", "auth_login": "TCH0001", "teacher_id": 1})

    response = client.get("/admin", headers=XHR)

    assert response.status_code == 403
    assert response.json()["message"] == "This workspace requires Admin access."


def test_admin_route_renders_placeholders_when_card_db_fails(client, monkeypatch):
    import backend.roles.admin.system_admin_cards as system_cards

    _patch_admin_page_context(monkeypatch)

    def fail_connect():
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(system_cards.queries, "connect_auth_db", fail_connect)
    _set_session(
        client,
        {
            "auth_role": "admin",
            "auth_login": "admin",
            "account_role": "system_admin",
            "canonical_role": "system_admin",
            "admin_id": 1,
            "admin_role": "owner",
        },
    )

    response = client.get("/admin")

    assert response.status_code == 200
    assert 'data-react-page="admin-home"' in response.text
    assert "Total Accounts" in response.text
    assert "Audit / Settings" in response.text
    assert "Placeholder" in response.text


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/admin"),
        ("GET", "/admin/api/students"),
        ("GET", "/admin/api/academic/gradebook"),
        ("GET", "/admin/api/announcements"),
        ("GET", "/admin/api/complaints"),
        ("GET", "/admin/api/resources"),
        ("POST", "/admin/api/students/{student_row_id}/parent-invite"),
        ("POST", "/admin/teachers"),
        ("POST", "/admin/parent-children"),
    ],
)
def test_existing_admin_routes_remain_registered(app, method, path):
    routes = _route_methods(app)

    assert path in routes
    assert method in routes[path]


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
