"""Academic Director staff registration and HOD subject-scope coverage."""

import json
import os
from base64 import b64encode

from itsdangerous import TimestampSigner
from werkzeug.security import check_password_hash

from backend.modules.domains.identity import staff_accounts as staff_registration
from backend.modules.domains.identity import staff_repository


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
        if "SELECT to_regclass(%s)" in sql:
            return _Result({"table_name": (params or ("",))[0]})
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


class _HodListConn:
    def __init__(self, missing_table=""):
        self.missing_table = missing_table
        self.params = []

    def execute(self, sql, params=None):
        self.params.append((sql, tuple(params or ())))
        if "SELECT to_regclass(%s)" in sql:
            table_name = (params or ("",))[0]
            return _Result({"table_name": None if table_name == self.missing_table else table_name})
        if "WHERE account.role = 'head_of_department'" in sql:
            return _Result(
                rows=[
                    {
                        "account_id": 80,
                        "login": "HOD0001",
                        "display_name": "Head of Math Department",
                        "role": "head_of_department",
                        "status": "active",
                        "subject_id": 5,
                        "subject_name": "Mathematics",
                        "scope_type": "head_of_department",
                        "created_at": "2026-07-06 10:00:00+00",
                        "updated_at": "2026-07-06 10:15:00+00",
                    }
                ]
            )
        raise AssertionError(f"Unexpected SQL: {sql}")


class _HodPasswordResetConn:
    def __init__(self, *, account_status="active"):
        self.account_status = account_status
        self.params = []
        self.committed = False

    def execute(self, sql, params=None):
        normalized_params = tuple(params or ())
        self.params.append((sql, normalized_params))
        if "FROM msi_v2.accounts" in sql and "FOR UPDATE" in sql:
            return _Result(
                {
                    "id": 80,
                    "login": "HOD0001",
                    "full_name": "Head of Math Department",
                    "status": self.account_status,
                    "legacy_source_table": "msi_staff",
                    "legacy_source_id": 40,
                }
            )
        if "UPDATE msi_v2.accounts" in sql and "RETURNING session_version" in sql:
            return _Result({"session_version": 4})
        if "UPDATE msi_v2.msi_staff" in sql:
            return _Result(None)
        if "INSERT INTO msi_v2.audit_events" in sql:
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


def test_academic_director_bootstrap_generates_ad_login_and_hashes_password():
    conn = _RegistrationConn()

    created, error, credentials = staff_registration._create_academic_director_account(
        conn,
        login="AD0001",
        display_name="Academic Director",
        commit=True,
    )

    assert created is True
    assert error == ""
    assert credentials["login"] == "AD0001"
    assert credentials["temporary_password"] == "AD0001"
    assert credentials["role"] == "academic_director"
    assert conn.committed is True

    stored_passwords = [
        params[1]
        for sql, params in conn.params
        if "INSERT INTO msi_v2.msi_staff" in sql or "INSERT INTO msi_v2.accounts" in sql
    ]
    assert stored_passwords
    for password_hash in stored_passwords:
        assert password_hash != "AD0001"
        assert check_password_hash(password_hash, "AD0001")


def test_list_head_of_department_accounts_returns_safe_display_payload():
    result = staff_repository._list_head_of_department_accounts(_HodListConn())

    assert result["warning"] == ""
    assert result["items"] == [
        {
            "account_id": 80,
            "login": "HOD0001",
            "display_name": "Head of Math Department",
            "role": "head_of_department",
            "status": "active",
            "subject_id": 5,
            "subject_name": "Mathematics",
            "scope_type": "head_of_department",
            "created_at": "2026-07-06 10:00:00+00",
            "updated_at": "2026-07-06 10:15:00+00",
        }
    ]
    assert "password_hash" not in result["items"][0]


def test_list_head_of_department_accounts_warns_when_scope_table_missing():
    result = staff_repository._list_head_of_department_accounts(
        _HodListConn(missing_table="msi_v2.staff_subject_scopes")
    )

    assert result["items"] == []
    assert "msi_v2.staff_subject_scopes" in result["warning"]


def test_academic_director_password_reset_hashes_both_hod_credentials_and_invalidates_sessions(monkeypatch):
    conn = _HodPasswordResetConn()
    monkeypatch.setattr(staff_registration, "_generate_temporary_password", lambda: "SafePass4826")

    reset, error, credentials = staff_registration._reset_head_of_department_password(
        conn,
        account_id=80,
        actor_account_id=12,
        actor_login="AD0001",
        commit=True,
    )

    assert reset is True
    assert error == ""
    assert credentials["login"] == "HOD0001"
    assert credentials["temporary_password"] == "SafePass4826"
    assert credentials["must_change_password"] is True
    assert conn.committed is True

    canonical_update = next(item for item in conn.params if "UPDATE msi_v2.accounts" in item[0])
    legacy_update = next(item for item in conn.params if "UPDATE msi_v2.msi_staff" in item[0])
    canonical_hash = canonical_update[1][0]
    legacy_hash = legacy_update[1][0]
    assert canonical_hash == legacy_hash
    assert canonical_hash != credentials["temporary_password"]
    assert check_password_hash(canonical_hash, credentials["temporary_password"])
    assert "must_change_password = true" in canonical_update[0]
    assert "session_version = session_version + 1" in canonical_update[0]
    assert "password_changed_at = NULL" in canonical_update[0]

    audit = next(item for item in conn.params if "INSERT INTO msi_v2.audit_events" in item[0])
    assert audit[1][0] == 12
    assert audit[1][1] == 80
    assert "SafePass4826" not in audit[1][2]
    assert "account.password_reset" in audit[0]


def test_disabled_head_of_department_password_cannot_be_reset(monkeypatch):
    conn = _HodPasswordResetConn(account_status="disabled")
    monkeypatch.setattr(staff_registration, "_generate_temporary_password", lambda: "SafePass4826")

    reset, error, credentials = staff_registration._reset_head_of_department_password(
        conn,
        account_id=80,
        actor_account_id=12,
    )

    assert reset is False
    assert error == "Head of Department account is disabled."
    assert credentials == {}
    assert not any("UPDATE msi_v2.accounts" in sql for sql, _ in conn.params)


def test_academic_director_can_create_hod_account_route(client, monkeypatch):
    import backend.modules.people.academic_director.workspace.api as academic_director_api

    monkeypatch.setattr(
        academic_director_api,
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
    _set_session(client, {"auth_role": "academic_director", "auth_login": "ad@test"})

    response = client.post(
        "/api/v1/academic-director/head-of-departments",
        data={"hod_display_name": "Head of Math Department", "hod_subject_id": "5"},
        headers=XHR,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    body = payload["data"]
    assert body["credentials"] == {
        "role": "head_of_department",
        "login": "HOD0001",
        "temporary_password": "HOD0001",
        "display_name": "Head of Math Department",
        "subject_name": "Mathematics",
    }
    assert "account_id" not in body["credentials"]
    assert "staff_id" not in body["credentials"]
    assert body["headOfDepartment"] == {
        "login": "HOD0001",
        "display_name": "Head of Math Department",
        "role": "head_of_department",
        "status": "active",
        "subject_name": "Mathematics",
    }
    assert "account_id" not in body["headOfDepartment"]
    assert "staff_id" not in body["headOfDepartment"]
    assert "password_hash" not in body["headOfDepartment"]


def test_academic_director_can_reset_hod_password_and_receives_it_once(client, monkeypatch):
    import backend.modules.people.academic_director.workspace.api as academic_director_api

    captured = {}

    def fake_reset(account_id, **kwargs):
        captured["account_id"] = account_id
        captured.update(kwargs)
        return (
            True,
            "",
            {
                "login": "HOD0001",
                "temporary_password": "SafePass4826",
                "display_name": "Head of Math Department",
                "must_change_password": True,
                "updated_at": "2026-07-13T10:00:00Z",
            },
        )

    monkeypatch.setattr(academic_director_api, "reset_head_of_department_password", fake_reset)
    _set_session(
        client,
        {"auth_role": "academic_director", "auth_login": "AD0001", "account_id": 12},
    )

    response = client.post(
        "/api/v1/academic-director/head-of-departments/80/reset-password",
        headers=XHR,
    )

    assert response.status_code == 200
    assert response.json()["data"] == {
        "message": "Temporary password generated.",
        "login": "HOD0001",
        "temporary_password": "SafePass4826",
        "display_name": "Head of Math Department",
        "must_change_password": True,
        "updated_at": "2026-07-13T10:00:00Z",
    }
    assert captured == {
        "account_id": 80,
        "actor_account_id": 12,
        "actor_login": "AD0001",
    }


def test_head_of_department_cannot_reset_another_hod_password(client, monkeypatch):
    import backend.modules.people.academic_director.workspace.api as academic_director_api

    def should_not_reset(*args, **kwargs):
        raise AssertionError("role dependency must reject this request before password reset")

    monkeypatch.setattr(academic_director_api, "reset_head_of_department_password", should_not_reset)
    _set_session(
        client,
        {"auth_role": "head_of_department", "auth_login": "HOD0001", "account_id": 80},
    )

    response = client.post(
        "/api/v1/academic-director/head-of-departments/81/reset-password",
        headers=XHR,
    )

    assert response.status_code == 403


def test_head_of_department_workspace_route_loads(client, monkeypatch):
    import backend.modules.people.head_of_department.workspace.page as hod_routes

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

    response = client.get("/head-of-departments")

    assert response.status_code == 200
    assert 'data-react-page="head-of-departments-home"' in response.text
    assert "Head of Departments Dashboard" in response.text
    assert "Subject Scope" in response.text


def test_head_of_department_can_access_subject_scoped_academy_page(client, monkeypatch):
    import backend.modules.people.head_of_department.workspace.page as hod_routes

    monkeypatch.setattr(
        hod_routes,
        "_head_of_department_academy_context",
        lambda: {
            "teachers": [],
            "academy_teachers": [{"id": 7, "subject_id": 5, "full_name": "Math Teacher"}],
            "group_options": [],
            "subjects": [{"id": 5, "subject_name": "Mathematics"}],
            "curriculum_programs": [],
            "curriculum_items": [],
        },
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

    response = client.get("/head-of-departments/teacher-academy")

    assert response.status_code == 200
    assert 'data-react-page="head-of-departments-academy"' in response.text
    assert 'data-react-page="internal-operations-home"' not in response.text
    assert "head_of_department" in response.text
    assert "managementAcademyTeachers" in response.text
    assert "Math Teacher" in response.text
    assert "Training tab" not in response.text


def test_hod_out_of_scope_academy_assessment_is_denied(client, monkeypatch):
    import backend.modules.people.head_of_department.workspace.staff_records_api as hod_api_routes

    monkeypatch.setattr(hod_api_routes, "can_user_manage_academy_teacher", lambda user, teacher_id: False)
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
        "/api/v1/head-of-department/teacher-academy/7/assessments",
        data={"lesson_assignment_id": "3"},
        headers=XHR,
    )

    assert response.status_code == 403
    assert response.json()["message"] == "This Teacher Academy teacher is outside your subject scope."


def test_academy_assessment_route_accepts_lesson_assignment_id(client, monkeypatch):
    import backend.modules.domains.teacher_academy.responses as academy_api

    captured = {}

    def fake_add_assessment(**kwargs):
        captured.update(kwargs)
        return True, ""

    monkeypatch.setattr(academy_api, "add_assessment", fake_add_assessment)
    monkeypatch.setattr(academy_api, "list_academy_teachers", lambda: [])
    monkeypatch.setattr(academy_api, "list_teachers", lambda: [])
    monkeypatch.setattr(academy_api, "filter_academy_teachers_for_user", lambda rows, user: rows)
    _set_session(client, {"auth_role": "academic_director", "auth_login": "AD0001"})

    response = client.post(
        "/api/v1/academic-director/teacher-academy/7/assessments",
        data={"lesson_assignment_id": "21", "decision": "passed"},
        headers=XHR,
    )

    assert response.status_code == 200
    assert response.json()["data"]["message"] == "Assessment saved."
    assert captured["academy_teacher_id"] == 7
    assert captured["lesson_assignment_id"] == "21"
    assert captured["decision"] == "passed"


def test_hod_out_of_scope_academy_schedule_is_denied(client, monkeypatch):
    import backend.modules.people.head_of_department.workspace.staff_records_api as hod_api_routes

    monkeypatch.setattr(hod_api_routes, "can_user_manage_academy_assignment", lambda user, assignment_id: False)
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
        "/api/v1/head-of-department/teacher-academy/assignments/21",
        data={"assignment_id": "21"},
        headers=XHR,
    )

    assert response.status_code == 403
    assert response.json()["message"] == "This Teacher Academy lesson is outside your subject scope."


def test_hod_filters_academy_rows_by_assigned_subject():
    from backend.modules.domains.teacher_academy.policies import filter_rows_by_subject_scope

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
