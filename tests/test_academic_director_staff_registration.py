"""Academic Director staff registration and HOD subject-scope coverage."""

import json
import os
from base64 import b64encode

from itsdangerous import TimestampSigner
from werkzeug.security import check_password_hash

from backend.roles.academic_director import staff_registration


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


class _Result:
    def __init__(self, row=None, rows=None):
        self._row = row
        self._rows = rows or []

    def fetchone(self):
        return self._row

    def fetchall(self):
        return self._rows


class _RegistrationConn:
    def __init__(self):
        self.params = []
        self.committed = False

    def execute(self, sql, params=None):
        self.params.append((sql, tuple(params or ())))
        if "to_regclass('msi_v2.accounts')" in sql:
            return _Result({"table_name": "msi_v2.accounts"})
        if "FROM msi_v2.subjects" in sql:
            return _Result({"id": 5, "subject_name": "Mathematics", "subject_key": "math"})
        if "regexp_replace(upper(login)" in sql:
            return _Result({"max_num": 0})
        if "INSERT INTO msi_v2.msi_staff" in sql:
            return _Result({"id": 40})
        if "FROM msi_v2.accounts" in sql:
            return _Result(None)
        if "INSERT INTO msi_v2.accounts" in sql:
            return _Result({"id": 80})
        if "FROM msi_v2.staff_profiles" in sql:
            return _Result(None)
        if "INSERT INTO msi_v2.staff_profiles" in sql:
            return _Result({"id": 90})
        if "INSERT INTO msi_v2.staff_subject_scopes" in sql:
            return _Result(None)
        raise AssertionError(f"Unexpected SQL: {sql}")

    def commit(self):
        self.committed = True


def test_academic_director_hod_service_generates_hod_login_and_hashes_password():
    conn = _RegistrationConn()

    created, error, credentials = staff_registration._create_head_of_department_account(
        conn,
        display_name="Head of Math Department",
        subject_id=5,
        created_by="academic-director",
        commit=True,
    )

    assert created is True
    assert error == ""
    assert credentials["login"] == "HOD0001"
    assert credentials["temporary_password"] == "HOD0001"
    assert credentials["role"] == "head_of_department"
    assert conn.committed is True

    stored_passwords = [
        params[1]
        for sql, params in conn.params
        if "INSERT INTO msi_v2.msi_staff" in sql or "INSERT INTO msi_v2.accounts" in sql
    ]
    assert stored_passwords
    for password_hash in stored_passwords:
        assert password_hash != "HOD0001"
        assert check_password_hash(password_hash, "HOD0001")


def test_academic_director_can_create_hod_account_route(client, monkeypatch):
    import backend.roles.academic_director.routes as academic_routes

    monkeypatch.setattr(
        academic_routes,
        "create_head_of_department_account",
        lambda **kwargs: (
            True,
            "",
            {
                "role": "head_of_department",
                "login": "HOD0001",
                "temporary_password": "HOD0001",
                "display_name": "Head of Math Department",
                "subject_name": "Mathematics",
                "account_id": 80,
                "staff_id": 40,
            },
        ),
    )
    monkeypatch.setattr(academic_routes, "invalidate_admin_page_context_cache", lambda: None)
    _set_session(client, {"auth_role": "academic_director", "auth_login": "ad@test"})

    response = client.post(
        "/academic-director/api/head-of-departments",
        data={"hod_display_name": "Head of Math Department", "hod_subject_id": "5"},
        headers=XHR,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["credentials"] == {
        "role": "head_of_department",
        "login": "HOD0001",
        "temporary_password": "HOD0001",
        "display_name": "Head of Math Department",
        "subject_name": "Mathematics",
    }
    assert "account_id" not in body["credentials"]
    assert "staff_id" not in body["credentials"]


def test_head_of_department_workspace_route_loads(client, monkeypatch):
    import backend.roles.head_of_department.routes as hod_routes

    monkeypatch.setattr(
        hod_routes,
        "head_of_department_workspace_cards",
        lambda: [{"label": "Subject Scope", "value": "1", "detail": "assigned subjects"}],
    )
    _set_session(
        client,
        {
            "auth_role": "head_of_department",
            "auth_login": "HOD0001",
            "account_id": 80,
            "staff_id": 40,
        },
    )

    response = client.get("/head-of-department")

    assert response.status_code == 200
    assert 'data-react-page="head-of-department-home"' in response.text
    assert "Head of Department Dashboard" in response.text
    assert "Subject Scope" in response.text


def test_head_of_department_can_access_subject_scoped_academy_page(client, monkeypatch):
    import backend.roles.admin.routes.admin_page as admin_page
    import backend.roles.head_of_department.academy_scope as academy_scope

    monkeypatch.setattr(
        admin_page,
        "build_admin_page_context",
        lambda **kwargs: {
            "panel": "teachers",
            "school_filter": "all",
            "sync_errors": [],
            "load_error": "",
            "admin_students": [],
            "admin_teachers": [],
            "admin_teacher_candidates": [],
            "admin_teacher_academy": [{"id": 7, "subject_id": 5, "full_name": "Math Teacher"}],
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
        },
    )
    monkeypatch.setattr(
        admin_page,
        "list_admin_academic_context",
        lambda: {
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
        },
    )
    monkeypatch.setattr(admin_page, "list_announcements", lambda: [])
    monkeypatch.setattr(admin_page, "system_admin_workspace_cards", lambda: [])
    monkeypatch.setattr(academy_scope, "filter_admin_context_for_current_hod", lambda page_context, academic_context: None)
    _set_session(
        client,
        {
            "auth_role": "head_of_department",
            "auth_login": "HOD0001",
            "account_id": 80,
            "staff_id": 40,
        },
    )

    response = client.get("/head-of-department/teacher-academy")

    assert response.status_code == 200
    assert 'data-react-page="admin-home"' in response.text
    assert "head_of_department" in response.text
    assert "adminTeacherAcademy" in response.text


def test_hod_out_of_scope_academy_assessment_is_denied(client, monkeypatch):
    import backend.roles.admin.routes.teacher_routes as teacher_routes

    monkeypatch.setattr(teacher_routes, "can_current_user_manage_academy_teacher", lambda teacher_id: False)
    _set_session(
        client,
        {
            "auth_role": "head_of_department",
            "auth_login": "HOD0001",
            "account_id": 80,
            "staff_id": 40,
        },
    )

    response = client.post(
        "/admin/teacher-academy/7/assessments",
        data={"lesson_assignment_id": "3"},
        headers=XHR,
    )

    assert response.status_code == 403
    assert response.json()["message"] == "This Teacher Academy teacher is outside your subject scope."


def test_hod_filters_academy_rows_by_assigned_subject():
    from backend.roles.head_of_department.academy_scope import filter_rows_by_subject_scope

    rows = [
        {"id": 1, "subject_id": 5, "full_name": "Math Teacher"},
        {"id": 2, "subject_id": 6, "full_name": "Chemistry Teacher"},
    ]

    assert filter_rows_by_subject_scope(rows, {5}) == [rows[0]]


def test_head_of_department_role_is_declared_in_phase1d_migration():
    from pathlib import Path

    migration = Path("database/alembic/versions/0004_head_of_department_subject_scopes.py").read_text()

    assert "'head_of_department'" in migration
    assert "CREATE TABLE IF NOT EXISTS msi_v2.staff_subject_scopes" in migration
    assert "idx_staff_subject_scopes_active" in migration
