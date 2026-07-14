import json
import os
from base64 import b64decode

import pytest
from itsdangerous import TimestampSigner


def _session_secret():
    return (
        os.environ.get("APP_SECRET_KEY", os.environ.get("FLASK_SECRET_KEY", "")).strip()
        or "dev-only-insecure-key-do-not-use-in-prod"
    )


def _decode_session(client):
    session_cookie = client.cookies.get("session")
    assert session_cookie
    unsigned = TimestampSigner(_session_secret()).unsign(session_cookie)
    return json.loads(b64decode(unsigned).decode("utf-8"))


def _telegram_context(telegram_user_id=9001, *, start_param=""):
    return {
        "telegram_user_id": telegram_user_id,
        "full_name": "Telegram User",
        "telegram_username": "telegram_user",
        "start_param": start_param,
    }


def _post_telegram_auth(client):
    return client.post("/auth/telegram", data={"init_data": "verified-init-data"})


def _auth_result(role, *, account_role=None, **session_overrides):
    account_role = account_role or role
    session_payload = {
        "account_id": 100,
        "account_role": account_role,
        "canonical_role": account_role,
        "auth_role": role,
        "session_version": 1,
        "auth_login": session_overrides.pop("auth_login", f"{account_role}@test"),
        **session_overrides,
    }
    return {
        "account": {"id": 100, "role": account_role, "login": session_payload["auth_login"]},
        "profile": {"role": account_role},
        "session": session_payload,
    }


def test_uses_account_telegram_links_service(client, monkeypatch):
    import backend.modules.identity.page as identity_routes

    calls = {}
    monkeypatch.setattr(identity_routes, "_telegram_auth_context", lambda init_data: _telegram_context(9002))
    monkeypatch.setattr(identity_routes, "_link_parent_from_telegram_start_param", lambda context: None)

    def fake_account_auth(telegram_user_id):
        calls["telegram_user_id"] = telegram_user_id
        return _auth_result(
            "student",
            auth_login="MSI00001",
            student_db_id=1001,
            student_id="MSI00001",
            student_full_name="Student User",
            student_enrollment_id=321,
            student_school_code="sehriyo",
        )

    monkeypatch.setattr(identity_routes, "authenticate_account_telegram", fake_account_auth)
    monkeypatch.setattr(identity_routes, "record_student_activity", lambda student_id: None)

    response = _post_telegram_auth(client)

    assert response.status_code == 200
    assert response.json()["redirect"] == "/dashboard/321?school=sehriyo"
    assert calls == {"telegram_user_id": 9002}


def test_active_parent_telegram_link_returns_parent(client, monkeypatch):
    import backend.modules.identity.page as identity_routes

    monkeypatch.setattr(identity_routes, "_telegram_auth_context", lambda init_data: _telegram_context(9001))
    monkeypatch.setattr(identity_routes, "_link_parent_from_telegram_start_param", lambda context: None)
    monkeypatch.setattr(
        identity_routes,
        "authenticate_account_telegram",
        lambda telegram_user_id: _auth_result(
            "parent",
            auth_login="parent@test",
            parent_id=50,
            parent_full_name="Parent User",
            telegram_user_id=telegram_user_id,
        ),
    )

    response = _post_telegram_auth(client)

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "linked": True,
        "role": "parent",
        "redirect": "/parent",
    }


def test_active_student_telegram_link_returns_dashboard_and_records_activity(
    client,
    monkeypatch,
):
    import backend.modules.identity.page as identity_routes

    activity_calls = []
    monkeypatch.setattr(identity_routes, "_telegram_auth_context", lambda init_data: _telegram_context(9002))
    monkeypatch.setattr(identity_routes, "_link_parent_from_telegram_start_param", lambda context: None)
    monkeypatch.setattr(
        identity_routes,
        "authenticate_account_telegram",
        lambda telegram_user_id: _auth_result(
            "student",
            auth_login="MSI00001",
            student_db_id=1001,
            student_id="MSI00001",
            student_full_name="Student User",
            student_enrollment_id=321,
            student_school_code="sehriyo",
            telegram_user_id=telegram_user_id,
        ),
    )
    monkeypatch.setattr(
        identity_routes,
        "record_student_activity",
        lambda student_id: activity_calls.append(student_id),
    )

    response = _post_telegram_auth(client)

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "linked": True,
        "role": "student",
        "redirect": "/dashboard/321?school=sehriyo",
    }
    assert activity_calls == [1001]


def test_active_teacher_telegram_link_is_not_a_portal_login(client, monkeypatch):
    import backend.modules.identity.page as identity_routes

    monkeypatch.setattr(identity_routes, "_telegram_auth_context", lambda init_data: _telegram_context(9003))
    monkeypatch.setattr(identity_routes, "_link_parent_from_telegram_start_param", lambda context: None)
    monkeypatch.setattr(
        identity_routes,
        "authenticate_account_telegram",
        lambda telegram_user_id: None,
    )

    response = _post_telegram_auth(client)

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "linked": False,
    }


def test_system_admin_telegram_link_returns_admin_compatibility(client, monkeypatch):
    import backend.modules.identity.page as identity_routes

    monkeypatch.setattr(identity_routes, "_telegram_auth_context", lambda init_data: _telegram_context(9004))
    monkeypatch.setattr(identity_routes, "_link_parent_from_telegram_start_param", lambda context: None)
    monkeypatch.setattr(
        identity_routes,
        "authenticate_account_telegram",
        lambda telegram_user_id: _auth_result(
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
            telegram_user_id=telegram_user_id,
        ),
    )

    response = _post_telegram_auth(client)

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "linked": True,
        "role": "system_admin",
        "redirect": "/internal/operations",
    }
    session_payload = _decode_session(client)
    assert session_payload["auth_role"] == "admin"
    assert session_payload["account_role"] == "system_admin"
    assert session_payload["canonical_role"] == "system_admin"
    assert session_payload["admin_id"] == 1


def test_missing_link_returns_safe_shape(client, monkeypatch):
    import backend.modules.identity.page as identity_routes

    monkeypatch.setattr(identity_routes, "_telegram_auth_context", lambda init_data: _telegram_context(9999))
    monkeypatch.setattr(identity_routes, "_link_parent_from_telegram_start_param", lambda context: None)
    monkeypatch.setattr(identity_routes, "authenticate_account_telegram", lambda telegram_user_id: None)

    response = _post_telegram_auth(client)

    assert response.status_code == 200
    assert response.json() == {"ok": True, "linked": False}


@pytest.mark.parametrize(
    ("case_name", "telegram_user_id"),
    [
        ("revoked_link", 9005),
        ("disabled_account", 9006),
        ("missing_profile", 9007),
    ],
)
def test_rejected_account_link_returns_safe_shape(
    client,
    monkeypatch,
    case_name,
    telegram_user_id,
):
    import backend.modules.identity.page as identity_routes

    assert case_name
    monkeypatch.setattr(
        identity_routes,
        "_telegram_auth_context",
        lambda init_data: _telegram_context(telegram_user_id),
    )
    monkeypatch.setattr(identity_routes, "_link_parent_from_telegram_start_param", lambda context: None)
    monkeypatch.setattr(identity_routes, "authenticate_account_telegram", lambda telegram_user_id: None)

    response = _post_telegram_auth(client)

    assert response.status_code == 200
    assert response.json() == {"ok": True, "linked": False}


def test_parent_invite_start_param_still_runs_before_account_auth(client, monkeypatch):
    import backend.modules.identity.page as identity_routes

    monkeypatch.setattr(
        identity_routes,
        "_telegram_auth_context",
        lambda init_data: _telegram_context(9001, start_param="parent_INVITE"),
    )
    monkeypatch.setattr(
        identity_routes,
        "_link_parent_from_telegram_start_param",
        lambda context: {
            "id": 50,
            "account_id": 100,
            "full_name": "Parent User",
            "telegram_username": "parent_user",
            "telegram_user_id": context["telegram_user_id"],
            "auth_result": _auth_result(
                "parent",
                auth_login="parent@test",
                parent_id=50,
                parent_full_name="Parent User",
                telegram_user_id=context["telegram_user_id"],
            ),
        },
    )

    def unexpected_account_auth(telegram_user_id):
        raise AssertionError("Parent invite linking must run before Account Authentication Telegram lookup")

    monkeypatch.setattr(identity_routes, "authenticate_account_telegram", unexpected_account_auth)

    response = _post_telegram_auth(client)

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "linked": True,
        "role": "parent",
        "redirect": "/parent",
    }


def test_success_json_shape_does_not_expose_raw_account_auth_objects(client, monkeypatch):
    import backend.modules.identity.page as identity_routes

    monkeypatch.setattr(identity_routes, "_telegram_auth_context", lambda init_data: _telegram_context(9001))
    monkeypatch.setattr(identity_routes, "_link_parent_from_telegram_start_param", lambda context: None)
    monkeypatch.setattr(
        identity_routes,
        "authenticate_account_telegram",
        lambda telegram_user_id: _auth_result(
            "parent",
            auth_login="parent@test",
            parent_id=50,
            parent_full_name="Parent User",
            telegram_user_id=telegram_user_id,
        ),
    )

    response = _post_telegram_auth(client)

    assert response.status_code == 200
    assert set(response.json()) == {"ok", "linked", "role", "redirect"}
    assert "account" not in response.json()
    assert "profile" not in response.json()
    assert "session" not in response.json()
    assert "link" not in response.json()
