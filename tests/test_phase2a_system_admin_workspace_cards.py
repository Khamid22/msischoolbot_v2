"""Admin overview access, preview gating, and route registration."""

import json
import os
from base64 import b64encode

import pytest
from itsdangerous import TimestampSigner

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

    def join_paths(prefix, path):
        if not prefix:
            return path
        if not path or path == "/":
            return prefix
        return f"{prefix.rstrip('/')}/{path.lstrip('/')}"

    def routes_already_include_prefix(route_list, prefix):
        if not prefix:
            return True
        for route in route_list:
            path = getattr(route, "path", None)
            if path is not None:
                return path == prefix or path.startswith(f"{prefix.rstrip('/')}/")
        return False

    def walk(route_list, prefix=""):
        for route in route_list:
            if type(route).__name__ == "_IncludedRouter":
                router_prefix = getattr(route.original_router, "prefix", "")
                next_prefix = (
                    prefix
                    if routes_already_include_prefix(route.original_router.routes, router_prefix)
                    else join_paths(prefix, router_prefix)
                )
                walk(route.original_router.routes, next_prefix)
                continue
            path = getattr(route, "path", None)
            methods = getattr(route, "methods", None)
            if path is not None and methods:
                routes.setdefault(join_paths(prefix, path), set()).update(methods)
            nested = getattr(route, "routes", None)
            if nested:
                walk(nested, prefix)

    walk(app.routes)
    return routes


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
        "admin_quick_stats": {
            "total_students": 141,
            "total_schools": 2,
            "total_teachers": 3,
            "total_subjects": 3,
            "total_groups": 19,
            "school_counts": [
                {"school_name": "School 5", "count": 96},
                {"school_name": "Sehriyo", "count": 45},
            ],
            "subject_counts": [
                {"subject_name": "IGCSE Mathematics A", "count": 96},
                {"subject_name": "English as a Second Language", "count": 43},
                {"subject_name": "IGCSE Chemistry", "count": 2},
            ],
            "group_counts": [
                {"subject_name": "IGCSE Mathematics A", "count": 13},
                {"subject_name": "IGCSE Chemistry", "count": 4},
                {"subject_name": "English as a Second Language", "count": 2},
            ],
        },
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


def test_system_admin_admin_can_access_admin_with_overview_stats(client, monkeypatch):
    _patch_admin_page_context(monkeypatch)
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
    # The account-identity cards are gone; the overview stat cards read
    # from the quick stats shipped with the page props.
    assert "Total Accounts" not in response.text
    assert "Telegram Links" not in response.text
    assert "systemAdminCards" not in response.text
    assert '"total_students":141' in response.text
    assert '"total_schools":2' in response.text
    assert '"total_teachers":3' in response.text
    assert '"total_subjects":3' in response.text
    assert '"total_groups":19' in response.text
    assert '"subject_counts"' in response.text
    assert '"group_counts"' in response.text
    assert "School 5" in response.text


def test_admin_preview_is_disabled_in_production_even_with_mode_param(client, monkeypatch):
    import backend.roles.admin.routes.admin_page as admin_page

    _patch_admin_page_context(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("ADMIN_PREVIEW_ROLES", raising=False)
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

    response = client.get("/admin?mode=student")

    assert response.status_code == 200
    assert '"devPreviewEnabled":false' in response.text
    assert '"previewRole":"admin"' in response.text
    assert '"adminMode":"admin"' in response.text


def test_admin_preview_can_be_explicitly_enabled_for_true_admin(client, monkeypatch):
    import backend.roles.admin.routes.admin_page as admin_page

    _patch_admin_page_context(monkeypatch)
    monkeypatch.setenv("ADMIN_PREVIEW_ROLES", "1")
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

    response = client.get("/admin?mode=student")

    assert response.status_code == 200
    assert '"devPreviewEnabled":true' in response.text
    assert '"previewRole":"student"' in response.text
    assert '"adminMode":"student"' in response.text


def test_wrong_role_is_denied_from_admin(client):
    _set_session(client, {"auth_role": "teacher", "auth_login": "TCH0001", "teacher_id": 1})

    response = client.get("/admin", headers=XHR)

    assert response.status_code == 403
    assert response.json()["message"] == "This workspace requires Admin access."


@pytest.mark.parametrize(
        ("method", "path"),
    [
        ("GET", "/admin"),
        ("GET", "/api/v1/admin/students"),
        ("GET", "/api/v1/admin/academic/gradebook"),
        ("GET", "/api/v1/admin/announcements"),
        ("GET", "/api/v1/admin/complaints"),
        ("GET", "/api/v1/admin/resources"),
        ("POST", "/api/v1/admin/students/{student_row_id}/parent-invite"),
        ("POST", "/admin/teachers"),
        ("POST", "/api/v1/admin/parent-children"),
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
