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
    import backend.modules.people.academic_director.workspace.page as academic_director_routes
    import backend.modules.people.head_of_department.workspace.page as head_of_department_routes
    import backend.modules.people.ceo.workspace.page as ceo_page

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
        head_of_department_routes,
        "head_of_department_workspace_cards",
        lambda: [{"label": "Subject Scope", "value": "1"}],
    )


@pytest.mark.parametrize(
    ("raw_role", "normalized", "path", "label"),
    [
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


def test_removed_admin_roles_have_no_permissions_or_workspace():
    for role in ("admin", "system_admin", "owner"):
        assert normalize_role(role) == ""
        assert dashboard_path_for_role(role) == "/"
        assert role_display_name(role) == "Unknown Role"
        assert has_permission(role, "view_global_reports") is False


def test_customer_support_permission_alias():
    assert has_permission("sales", "view_tickets") is True
    assert has_permission("sales", "manage_curriculum_progress") is False


@pytest.mark.parametrize(
    ("role", "path", "page"),
    [
        ("ceo", "/ceo", "ceo-home"),
        ("customer_support", "/customer-support/dashboard", "customer-support-home"),
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


def test_invalid_session_role_fails_closed(client):
    _set_session(client, {"auth_role": "ghost", "auth_login": "ghost@test"})

    response = client.get("/ceo", headers=XHR)

    assert response.status_code == 403
    assert response.json() == {"status": "error", "message": "Invalid session role."}
