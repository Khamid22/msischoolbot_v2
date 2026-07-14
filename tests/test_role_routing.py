"""Canonical role helpers and role route guards."""

import json
import os
from base64 import b64encode

import pytest
from itsdangerous import TimestampSigner

from backend.core.access.workspace_permissions import (
    has_workspace_permission as has_permission,
)
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
    import backend.workspaces.academic_director.page as academic_director_routes
    import backend.workspaces.head_of_departments.page as head_of_department_routes
    import backend.workspaces.ceo.page as ceo_page
    import backend.workspaces.customer_support.page as customer_support_page

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
        head_of_department_routes,
        "head_of_department_workspace_cards",
        lambda: [{"label": "Subject Scope", "value": "1"}],
    )


@pytest.mark.parametrize(
    ("raw_role", "normalized", "path", "label"),
    [
        ("owner", "admin", "/internal/operations", "Admin"),
        ("system_admin", "system_admin", "/internal/operations", "System Admin"),
        ("sales", "customer_support", "/customer-support", "Customer Support"),
        ("academic-director", "academic_director", "/academic-director", "Academic Director"),
        ("hod", "head_of_department", "/head-of-departments", "Head of Departments"),
        ("parent", "parent", "/parent", "Parent"),
    ],
)
def test_role_aliases_normalize_to_dashboard_paths(raw_role, normalized, path, label):
    assert normalize_role(raw_role) == normalized
    assert dashboard_path_for_role(raw_role) == path
    assert role_display_name(raw_role) == label


def test_teacher_has_a_portal_destination():
    assert normalize_role("teacher") == "teacher"
    assert dashboard_path_for_role("teacher") == "/teacher"
    assert role_display_name("teacher") == "Teacher"


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
        ("customer_support", "/customer-support", "customer-support-home"),
        ("academic_director", "/academic-director", "academic-director-home"),
        ("head_of_department", "/head-of-departments", "head-of-departments-home"),
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


def test_hr_role_aliases_route_to_the_recruitment_workspace():
    for role in ("hr", "hr-manager", "hr_manager", "hr manager"):
        assert normalize_role(role) == "hr_manager"
        assert dashboard_path_for_role(role) == "/hr-manager"
        assert role_display_name(role) == "HR Manager"


def test_hr_role_can_initialize_staff_session_and_routes_to_its_workspace(client, monkeypatch):
    import backend.modules.identity.page as identity_page

    monkeypatch.setattr(
        identity_page,
        "_load_admin_handoff_payload",
        lambda _token: ({"id": 91, "login": "former-hr", "role": "hr_manager"}, ""),
    )

    response = client.get("/admin/continue?handoff=test")

    assert response.status_code == 302
    assert response.headers["location"] == "/hr-manager"


def test_invalid_session_role_fails_closed(client):
    _set_session(client, {"auth_role": "ghost", "auth_login": "ghost@test"})

    response = client.get("/ceo", headers=XHR)

    assert response.status_code == 403
    assert response.json() == {"status": "error", "message": "Invalid session role."}
