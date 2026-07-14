"""Phase 2A-3D Student dashboard safety tests."""

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


def _student_session(**overrides):
    payload = {
        "auth_role": "student",
        "auth_login": "MSI0001",
        "student_db_id": 1001,
        "student_id": "MSI0001",
        "student_full_name": "Example Learner",
        "student_enrollment_id": 321,
        "student_school_code": "sehriyo",
    }
    payload.update(overrides)
    return payload


def _dashboard_payload(student_id=321):
    return {
        "student": {
            "id": student_id,
            "fullName": "Example Learner",
            "initials": "EL",
            "group": "Example Group",
            "subject": "Mathematics",
            "subjectCode": "MATH",
            "schoolCode": "sehriyo",
            "schoolName": "Example School",
            "coins": 12,
        },
        "attendanceRecord": {
            "totalCount": 10,
            "presentCount": 8,
            "absentCount": 1,
            "justifiedAbsentCount": 1,
        },
        "homeworkGrades": [{"lesson": "1", "score": 8}],
        "examResults": [{"label": "Checkpoint", "score": 7}],
        "averageGrade": 8,
        "coins": 12,
    }


def _dashboard_context(student_id=321):
    payload = _dashboard_payload(student_id)
    return {
        "payload": payload,
        "attendance_rate": 90,
        "exam_performance": 7,
        "program_completed_lessons": 45,
        "program_completed_rate": 25,
        "rating_board_url": f"/dashboard/{student_id}/rating-board",
        "resources_url": f"/dashboard/{student_id}/resources",
        "aap_lessons_url": f"/dashboard/{student_id}/aap-lessons",
        "ar_lessons_url": f"/dashboard/{student_id}/ar-lessons",
        "current_subject_name": "Mathematics",
        "current_subject_short_name": "MATH",
        "subject_switch_options": [
            {
                "subject": "Mathematics",
                "subject_short": "MATH",
                "group": "Example Group",
                "url": f"/dashboard/{student_id}?subject=Mathematics&group=Example Group",
                "is_current": True,
            }
        ],
        "student_profile": {
            "group_name": "Example Group",
            "school_name": "Example School",
            "teacher_name": "Example Teacher",
            "classmates": [],
        },
        "profile_notice": "",
        "profile_error": "",
        "dashboard_back_url": "/",
        "show_dashboard_back": False,
        "refresh_url": f"/dashboard/{student_id}?refresh=1",
        "last_updated_label": "Last Update: --.",
    }


def _patch_student_home(monkeypatch):
    import backend.workspaces.student.page as student_page

    monkeypatch.setattr(
        student_page,
        "build_student_panel_context",
        lambda **kwargs: {
            "subjects": [],
            "groups_by_subject": {},
            "students_by_subject_group": {},
            "form_data": {},
            "load_error": "",
        },
    )


def _patch_valid_dashboard(monkeypatch, student_id=321):
    import backend.workspaces.student.dashboard as dashboard_routes

    monkeypatch.setattr(
        dashboard_routes.payload_service,
        "load_student_payload_for_view",
        lambda **kwargs: (_dashboard_payload(student_id), {}, "", 200),
    )
    monkeypatch.setattr(
        dashboard_routes.dashboard_service,
        "build_dashboard_page_context",
        lambda **kwargs: _dashboard_context(student_id),
    )
    monkeypatch.setattr(dashboard_routes, "list_announcements", lambda include_drafts=False: [])


def test_student_route_redirects_to_session_dashboard(client):
    _set_session(client, _student_session())

    response = client.get("/student")

    assert response.status_code == 302
    assert response.headers["location"] == "/dashboard/321?school=sehriyo"


def test_student_route_without_enrollment_renders_student_home(client, monkeypatch):
    _patch_student_home(monkeypatch)
    session_payload = _student_session()
    session_payload.pop("student_enrollment_id")
    _set_session(client, session_payload)

    response = client.get("/student")

    assert response.status_code == 200
    assert 'data-react-page="student-home"' in response.text


def test_dashboard_renders_with_mocked_valid_payload(client, monkeypatch):
    _patch_valid_dashboard(monkeypatch, student_id=321)
    _set_session(client, _student_session())

    response = client.get("/dashboard/321")

    assert response.status_code == 200
    assert 'data-react-page="student-dashboard"' in response.text
    assert "attendanceRate" in response.text
    assert "examPerformance" in response.text
    assert "programCompletedRate" in response.text
    assert "90" in response.text
    assert "7" in response.text
    assert "25" in response.text


def test_student_cannot_access_another_dashboard(client, monkeypatch):
    import backend.modules.people.students.payload as payload_service

    monkeypatch.setattr(
        payload_service,
        "load_dashboard_payload",
        lambda **kwargs: (_dashboard_payload(kwargs["student_id"]), {}, None),
    )
    _set_session(client, _student_session(student_enrollment_id=321))

    response = client.get("/dashboard/999")

    assert response.status_code == 403
    assert 'data-react-page="student-not-found"' in response.text
    assert "Access denied: you can open only your own dashboard." in response.text


def test_teacher_role_cannot_open_student_dashboard(client, monkeypatch):
    import backend.modules.people.students.payload as payload_service

    monkeypatch.setattr(
        payload_service,
        "load_dashboard_payload",
        lambda **kwargs: (_dashboard_payload(kwargs["student_id"]), {}, None),
    )
    _set_session(
        client,
        {
            "auth_role": "teacher",
            "auth_login": "TCH0001",
            "teacher_id": 42,
        },
    )

    response = client.get("/dashboard/321")

    assert response.status_code == 403


def test_parent_child_dashboard_redirects_to_public_dashboard(client, monkeypatch):
    import backend.workspaces.parent.page as parent_routes

    monkeypatch.setattr(parent_routes, "parent_can_access_student", lambda parent_id, student_row_id: True)
    monkeypatch.setattr(
        parent_routes,
        "resolve_parent_child_dashboard",
        lambda student_row_id: {
            "student_id": 654,
            "subject": "Mathematics",
            "group": "Example Group",
            "school": "sehriyo",
        },
    )
    _set_session(client, {"auth_role": "parent", "auth_login": "parent@example", "parent_id": 50})

    response = client.get("/parent/dashboard/101")

    assert response.status_code == 302
    location = response.headers["location"]
    assert location.startswith("/dashboard/654?")
    assert "subject=Mathematics" in location
    assert "group=Example%20Group" in location
    assert "school=sehriyo" in location
    assert "parent_return=1" in location


def test_unlinked_parent_child_dashboard_returns_access_denied(client, monkeypatch):
    import backend.workspaces.parent.page as parent_routes

    monkeypatch.setattr(parent_routes, "parent_can_access_student", lambda parent_id, student_row_id: False)
    _set_session(client, {"auth_role": "parent", "auth_login": "parent@example", "parent_id": 50})

    response = client.get("/parent/dashboard/101")

    assert response.status_code == 403
    assert "Access denied" in response.text
    assert "This student is not linked to your parent account." in response.text


def test_parent_direct_dashboard_access_uses_parent_validation(client, monkeypatch):
    import backend.workspaces.student.dashboard as dashboard_routes
    import backend.modules.people.students.payload as payload_service

    calls = []
    monkeypatch.setattr(
        payload_service,
        "load_dashboard_payload",
        lambda **kwargs: (_dashboard_payload(kwargs["student_id"]), {}, None),
    )
    monkeypatch.setattr(
        payload_service,
        "parent_can_access_dashboard",
        lambda parent_id, dashboard_student_id: calls.append((parent_id, dashboard_student_id)) or True,
    )
    monkeypatch.setattr(
        dashboard_routes.dashboard_service,
        "build_dashboard_page_context",
        lambda **kwargs: _dashboard_context(654),
    )
    monkeypatch.setattr(dashboard_routes, "list_announcements", lambda include_drafts=False: [])
    _set_session(client, {"auth_role": "parent", "auth_login": "parent@example", "parent_id": 50})

    response = client.get("/dashboard/654")

    assert response.status_code == 200
    assert 'data-react-page="student-dashboard"' in response.text
    assert calls == [(50, 654)]


def test_admin_student_dashboard_redirects_to_embed_dashboard(client, monkeypatch):
    import backend.internal_operations.people.students.form_routes as student_routes

    monkeypatch.setattr(
        student_routes,
        "resolve_student_for_internal_operations",
        lambda student_row_id, get_profile: (
            {
                "student_id": 654,
                "subject": "Mathematics",
                "group": "Example Group",
                "school": "sehriyo",
            },
            "",
            200,
        ),
    )
    _set_session(
        client,
        {
            "auth_role": "admin",
            "auth_login": "admin",
            "admin_id": 1,
            "admin_role": "owner",
            "admin_last_school": "all",
        },
    )

    response = client.get("/admin/students/101/dashboard")

    assert response.status_code == 302
    location = response.headers["location"]
    assert location.startswith("/dashboard/654?")
    assert "embed=admin" in location
    assert "admin_return_panel=students" in location
    assert "admin_return_school=all" in location


def test_admin_student_dashboard_target_preserves_embed_admin(client, monkeypatch):
    import backend.internal_operations.people.students.form_routes as student_routes

    monkeypatch.setattr(
        student_routes,
        "resolve_student_for_internal_operations",
        lambda student_row_id, get_profile: (
            {
                "student_id": 654,
                "subject": "Mathematics",
                "group": "Example Group",
                "school": "sehriyo",
            },
            "",
            200,
        ),
    )
    _set_session(
        client,
        {
            "auth_role": "admin",
            "auth_login": "admin",
            "admin_id": 1,
            "admin_role": "owner",
            "admin_last_school": "all",
        },
    )

    response = client.get("/admin/students/101/dashboard/resources")

    assert response.status_code == 302
    location = response.headers["location"]
    assert location.startswith("/dashboard/654/resources?")
    assert "embed=admin" in location
    assert "admin_return_panel=students" in location


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/"),
        ("POST", "/login"),
        ("POST", "/auth/telegram"),
        ("GET", "/student"),
        ("GET", "/dashboard/{student_id}"),
        ("GET", "/dashboard/{student_id}/resources"),
        ("GET", "/dashboard/{student_id}/chat"),
        ("GET", "/dashboard/{student_id}/office-hours"),
        ("GET", "/admin"),
        ("GET", "/parent"),
        ("GET", "/api/v1/auth/me"),
    ],
)
def test_existing_critical_routes_remain_registered(app, method, path):
    routes = _route_methods(app)

    assert path in routes
    assert method in routes[path]
