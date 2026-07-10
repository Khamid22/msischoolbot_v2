"""Phase 2A-3A teacher workspace cards."""

import json
import os
from base64 import b64encode

import pytest
from itsdangerous import TimestampSigner

from backend.modules.teachers.cards import build_teacher_workspace_cards


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


def _teacher_workspace():
    return {
        "teacher": {
            "id": 42,
            "full_name": "Example Teacher",
            "login": "TCH0001",
            "assigned_group": "A1",
            "category": "",
            "semester_stage": "",
            "performance_score": 7.0,
        },
        "groups": [
            {
                "group": {"id": 10, "name": "A1"},
                "lessons": [],
                "enrollments": [
                    {"enrollmentId": 101, "fullName": "Student One"},
                    {"enrollmentId": 102, "fullName": "Student Two"},
                ],
            },
            {
                "group": {"id": 11, "name": "A2"},
                "lessons": [],
                "enrollments": [
                    {"enrollmentId": 103, "fullName": "Student Three"},
                ],
            },
        ],
        "academy": None,
        "journey": [],
        "lesson_reports": [],
        "training_timetable": [],
    }


class _Rows:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class _SubjectConnection:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def execute(self, sql, params=None):
        return _Rows([{"id": 1, "name": "Mathematics"}])


def test_teacher_workspace_card_provider_counts_groups_and_students():
    cards = build_teacher_workspace_cards(
        teacher_id=42,
        teacher_staff_id=7,
        workspace=_teacher_workspace(),
    )

    assert cards == [
        {
            "label": "Assigned Groups",
            "value": "2",
            "detail": "active teaching groups",
            "tone": "text-slate-900",
        },
        {
            "label": "Students",
            "value": "3",
            "detail": "in assigned groups",
            "tone": "text-slate-900",
        },
        {
            "label": "Resources",
            "value": "Placeholder",
            "detail": "teacher resources later",
            "tone": "text-blue-600",
        },
        {
            "label": "Attendance/Homework",
            "value": "Placeholder",
            "detail": "teacher actions later",
            "tone": "text-emerald-600",
        },
    ]


@pytest.mark.parametrize(
    ("teacher_id", "workspace"),
    [
        (None, _teacher_workspace()),
        (42, None),
    ],
)
def test_teacher_workspace_card_provider_returns_placeholders(teacher_id, workspace):
    cards = build_teacher_workspace_cards(
        teacher_id=teacher_id,
        teacher_staff_id=None,
        workspace=workspace,
    )

    assert cards[0]["value"] == "-"
    assert cards[1]["value"] == "-"
    assert cards[2]["value"] == "Placeholder"
    assert cards[3]["value"] == "Placeholder"


def test_teacher_route_loads_and_shows_mocked_cards(client, monkeypatch):
    import backend.modules.teachers.service as teacher_service
    import backend.modules.teachers.page as teacher_routes
    import database

    monkeypatch.setattr(teacher_routes, "build_teacher_workspace", lambda teacher_id, staff_id=None: _teacher_workspace())
    monkeypatch.setattr(teacher_service, "get_teacher_by_id", lambda teacher_id: {"assigned_group": "A1"})
    monkeypatch.setattr(database, "connect_auth_db", lambda: _SubjectConnection())
    _set_session(
        client,
        {
            "auth_role": "teacher",
            "auth_login": "TCH0001",
            "teacher_id": 42,
            "teacher_staff_id": 7,
        },
    )

    response = client.get("/teacher")

    assert response.status_code == 200
    assert 'data-react-page="teacher-home"' in response.text
    assert "Assigned Groups" in response.text
    assert "Students" in response.text
    assert "Resources" in response.text
    assert "Attendance/Homework" in response.text
    assert "2" in response.text
    assert "3" in response.text


def test_wrong_role_is_denied_from_teacher_workspace(client):
    _set_session(client, {"auth_role": "student", "auth_login": "MSI00001"})

    response = client.get("/teacher", headers=XHR)

    assert response.status_code == 401
    assert response.json() == {
        "ok": False,
        "message": "Teacher authentication required.",
    }


def test_teacher_route_db_failure_returns_placeholder_cards(client, monkeypatch):
    import backend.modules.teachers.service as teacher_service
    import backend.modules.teachers.page as teacher_routes
    import database

    def fail_workspace(teacher_id, staff_id=None):
        raise RuntimeError("database unavailable")

    def fail_db(*args, **kwargs):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(teacher_routes, "build_teacher_workspace", fail_workspace)
    monkeypatch.setattr(teacher_service, "get_teacher_by_id", fail_db)
    monkeypatch.setattr(database, "connect_auth_db", fail_db)
    _set_session(
        client,
        {
            "auth_role": "teacher",
            "auth_login": "TCH0001",
            "teacher_id": 42,
            "teacher_staff_id": 7,
        },
    )

    response = client.get("/teacher")

    assert response.status_code == 200
    assert 'data-react-page="teacher-home"' in response.text
    assert "Assigned Groups" in response.text
    assert "Resources" in response.text
    assert "Placeholder" in response.text


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
