"""Canonical role helpers and role route guards."""

import json
import os
from base64 import b64encode

import pytest
from itsdangerous import TimestampSigner

from backend.core.access.permissions import has_permission
from backend.core.access.roles import (
    dashboard_path_for_role,
    normalize_role,
    role_display_name,
)

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


def _patch_workspace_cards(monkeypatch):
    import backend.pages.academics.director as academic_director_routes
    import backend.pages.academics.hod as head_of_department_routes
    import backend.pages.staff.ceo as ceo_page
    import backend.pages.staff.support as customer_support_page
    import backend.pages.staff.hr as hr_manager_page

    monkeypatch.setattr(
        ceo_page,
        "ceo_workspace_cards",
        lambda: [{"label": "Schools", "value": "2"}],
    )
    monkeypatch.setattr(
        academic_director_routes,
        "academic_director_workspace_cards",
        lambda: [{"label": "Groups", "value": "8"}],
    )
    monkeypatch.setattr(
        customer_support_page,
        "customer_support_workspace_cards",
        lambda: [{"label": "Parents", "value": "4"}],
    )
    monkeypatch.setattr(
        hr_manager_page,
        "hr_manager_workspace_cards",
        lambda: [{"label": "Teachers", "value": "3"}],
    )
    monkeypatch.setattr(
        head_of_department_routes,
        "head_of_department_workspace_cards",
        lambda: [{"label": "Subject Scope", "value": "1"}],
    )


@pytest.mark.parametrize(
    ("raw_role", "normalized", "path", "label"),
    [
        ("owner", "admin", "/admin", "Admin"),
        ("system_admin", "system_admin", "/admin", "System Admin"),
        ("hr", "hr_manager", "/hr", "HR Manager"),
        ("sales", "customer_support", "/support", "Customer Support"),
        ("academic-director", "academic_director", "/academic-director", "Academic Director"),
        ("hod", "head_of_department", "/head-of-department", "Head of Department"),
        ("teacher", "teacher", "/teacher", "Teacher"),
        ("parent", "parent", "/parent", "Parent"),
    ],
)
def test_role_aliases_normalize_to_dashboard_paths(raw_role, normalized, path, label):
    assert normalize_role(raw_role) == normalized
    assert dashboard_path_for_role(raw_role) == path
    assert role_display_name(raw_role) == label


def test_admin_has_all_permissions():
    assert has_permission("admin", "view_global_reports") is True
    assert has_permission("system_admin", "view_global_reports") is True
    assert has_permission("admin", "delete_the_moon") is True
    assert has_permission("system_admin", "delete_the_moon") is True


def test_customer_support_permission_alias():
    assert has_permission("sales", "view_tickets") is True
    assert has_permission("sales", "manage_curriculum_progress") is False


@pytest.mark.parametrize(
    ("role", "path", "page"),
    [
        ("ceo", "/ceo", "ceo-home"),
        ("hr_manager", "/hr", "hr-home"),
        ("customer_support", "/support", "support-home"),
        ("academic_director", "/academic-director", "academic-director-home"),
        ("head_of_department", "/head-of-department", "head-of-department-home"),
        ("parent", "/parent", "parent-home"),
    ],
)
def test_role_home_routes_render_for_matching_role(client, monkeypatch, role, path, page):
    _patch_workspace_cards(monkeypatch)
    payload = {
        "auth_role": role,
        "auth_login": f"{role}@test",
        "parent_id": 1 if role == "parent" else 0,
    }
    _set_session(client, payload)

    response = client.get(path)

    assert response.status_code == 200
    assert f'data-react-page="{page}"' in response.text


def test_student_role_entry_redirects_to_own_dashboard(client):
    _set_session(
        client,
        {
            "auth_role": "student",
            "auth_login": "MSI0001",
            "student_db_id": 1,
            "student_enrollment_id": 321,
            "student_school_code": "sehriyo",
        },
    )

    response = client.get("/student")

    assert response.status_code == 302
    assert response.headers["location"] == "/dashboard/321?school=sehriyo"


def test_wrong_role_route_returns_403_json(client):
    _set_session(client, {"auth_role": "ceo", "auth_login": "ceo@test"})

    response = client.get("/hr", headers=XHR)

    assert response.status_code == 403
    assert response.json()["message"] == "This page requires HR Manager access."


def test_invalid_session_role_fails_closed(client):
    _set_session(client, {"auth_role": "ghost", "auth_login": "ghost@test"})

    response = client.get("/ceo", headers=XHR)

    assert response.status_code == 403
    assert response.json() == {"status": "error", "message": "Invalid session role."}
