import json
import os
from base64 import b64encode

import pytest
from itsdangerous import TimestampSigner


CSRF = "phase1c-csrf"


def _session_secret():
    return (
        os.environ.get("APP_SECRET_KEY", os.environ.get("FLASK_SECRET_KEY", "")).strip()
        or "dev-only-insecure-key-do-not-use-in-prod"
    )


def _signed_session(data):
    encoded = b64encode(json.dumps(data).encode("utf-8"))
    return TimestampSigner(_session_secret()).sign(encoded).decode("utf-8")


def _set_csrf_session(client):
    client.cookies.set("session", _signed_session({"csrf_token": CSRF}))


def _post_login(client, login, password="correct-password"):
    return client.post(
        "/login",
        data={
            "login": login,
            "password": password,
            "csrf_token": CSRF,
        },
    )


def _auth_result(role, *, account_role=None, **session_overrides):
    account_role = account_role or role
    session_payload = {
        "account_id": 100,
        "account_role": account_role,
        "canonical_role": account_role,
        "auth_role": role,
        "auth_login": session_overrides.pop("auth_login", f"{account_role}@test"),
        **session_overrides,
    }
    return {
        "account": {"id": 100, "role": account_role, "login": session_payload["auth_login"]},
        "profile": {"role": account_role},
        "session": session_payload,
    }


def test_flag_off_legacy_login_path_still_used(client, monkeypatch):
    import backend.domains.identity.routes as identity_routes

    _set_csrf_session(client)
    calls = {"legacy_student": 0, "auth_v2": 0, "activity": 0}

    monkeypatch.setattr(identity_routes, "account_auth_v2_enabled", lambda: False)

    def unexpected_auth_v2(login, password):
        calls["auth_v2"] += 1
        raise AssertionError("Auth V2 must not be called when the flag is off")

    def fake_verify_student_credentials(login, password):
        calls["legacy_student"] += 1
        return {
            "id": 1001,
            "full_name": "Student User",
            "student_id": "MSI00001",
            "subjects": "",
            "school_code": "sehriyo",
            "telegram_user_id": None,
            "enrollment_id": 321,
        }

    def fake_record_student_activity(student_id):
        calls["activity"] += 1
        return {"updated": True}

    monkeypatch.setattr(identity_routes, "authenticate_account_password", unexpected_auth_v2)
    monkeypatch.setattr(identity_routes, "verify_student_credentials", fake_verify_student_credentials)
    monkeypatch.setattr(identity_routes, "record_student_activity", fake_record_student_activity)

    response = _post_login(client, "MSI00001")

    assert response.status_code == 302
    assert response.headers["location"] == "/dashboard/321?school=sehriyo"
    assert calls == {"legacy_student": 1, "auth_v2": 0, "activity": 1}


def test_flag_on_student_login_uses_accounts(client, monkeypatch):
    import backend.domains.identity.routes as identity_routes

    _set_csrf_session(client)
    calls = {"activity": []}
    monkeypatch.setattr(identity_routes, "account_auth_v2_enabled", lambda: True)

    def fake_auth(login, password):
        calls["login"] = login
        calls["password"] = password
        return _auth_result(
            "student",
            auth_login="MSI00001",
            student_db_id=1001,
            student_id="MSI00001",
            student_full_name="Student User",
            student_enrollment_id=321,
            student_school_code="sehriyo",
        )

    monkeypatch.setattr(identity_routes, "authenticate_account_password", fake_auth)
    monkeypatch.setattr(
        identity_routes,
        "record_student_activity",
        lambda student_id: calls["activity"].append(student_id),
    )

    response = _post_login(client, "MSI00001")

    assert response.status_code == 302
    assert response.headers["location"] == "/dashboard/321?school=sehriyo"
    assert calls == {
        "login": "MSI00001",
        "password": "correct-password",
        "activity": [1001],
    }


def test_flag_on_teacher_tch0001_login_uses_accounts(client, monkeypatch):
    import backend.domains.identity.routes as identity_routes

    _set_csrf_session(client)
    monkeypatch.setattr(identity_routes, "account_auth_v2_enabled", lambda: True)
    monkeypatch.setattr(
        identity_routes,
        "authenticate_account_password",
        lambda login, password: _auth_result(
            "teacher",
            auth_login="TCH0001",
            teacher_id=10,
            teacher_staff_id=2,
            teacher_full_name="Teacher User",
            teacher_group="IGCSE",
        ),
    )

    response = _post_login(client, "TCH0001")

    assert response.status_code == 302
    assert response.headers["location"] == "/teacher"


def test_flag_on_system_admin_reaches_admin_compatibility(client, monkeypatch):
    import backend.domains.identity.routes as identity_routes

    _set_csrf_session(client)
    monkeypatch.setattr(identity_routes, "account_auth_v2_enabled", lambda: True)
    monkeypatch.setattr(
        identity_routes,
        "authenticate_account_password",
        lambda login, password: _auth_result(
            "admin",
            account_role="system_admin",
            auth_login="admin",
            staff_id=1,
            staff_role="system_admin",
            admin_id=1,
            admin_role="owner",
            admin_is_owner=True,
            admin_last_panel="overview",
            admin_last_school="all",
        ),
    )

    response = _post_login(client, "admin")

    assert response.status_code == 302
    assert response.headers["location"] == "/admin"


@pytest.mark.parametrize(
    "login",
    [
        "disabled-account",
        "pending-account",
        "wrong-password",
        "unknown-role",
    ],
)
def test_flag_on_rejected_account_returns_401(client, monkeypatch, login):
    import backend.domains.identity.routes as identity_routes

    _set_csrf_session(client)
    monkeypatch.setattr(identity_routes, "account_auth_v2_enabled", lambda: True)
    monkeypatch.setattr(identity_routes, "authenticate_account_password", lambda login_value, password: None)

    response = _post_login(client, login)

    assert response.status_code == 401
    assert response.headers["content-type"].startswith("text/html")
    assert "Invalid login or password" in response.text
