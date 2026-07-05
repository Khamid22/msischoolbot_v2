import importlib
import json
import os
from base64 import b64encode

import pytest
from fastapi import FastAPI
from itsdangerous import TimestampSigner
from starlette.testclient import TestClient


CSRF = "phase1d-structure-safety"


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


def _post_login(client, login="MSI00001", password="correct-password"):
    return client.post(
        "/login",
        data={
            "login": login,
            "password": password,
            "csrf_token": CSRF,
        },
    )


def _rate_limit_isolated_client(app, label):
    return TestClient(
        app,
        follow_redirects=False,
        client=(f"phase1d-{label}", 50000),
    )


def _auth_v2_result(role, *, account_role=None, **session_overrides):
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


def test_backend_server_create_app_imports_and_title_stays_expected():
    from backend.server import create_app

    app = create_app()

    assert isinstance(app, FastAPI)
    assert app.title == "MSI School API"


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
def test_critical_routes_remain_registered(app, method, path):
    routes = _route_methods(app)

    assert path in routes
    assert method in routes[path]


def test_account_auth_v2_flag_off_keeps_legacy_login_path_available(app, monkeypatch):
    import backend.domains.identity.routes as identity_routes

    client = _rate_limit_isolated_client(app, "legacy-login")
    calls = {"legacy": 0, "auth_v2": 0}
    _set_csrf_session(client)
    monkeypatch.setattr(identity_routes, "account_auth_v2_enabled", lambda: False)

    def unexpected_auth_v2(login, password):
        calls["auth_v2"] += 1
        raise AssertionError("Auth V2 must not run when ACCOUNT_AUTH_V2_ENABLED=0")

    def fake_legacy_student(login, password):
        calls["legacy"] += 1
        return {
            "id": 1001,
            "full_name": "Example Student",
            "student_id": "MSI00001",
            "subjects": "",
            "school_code": "sehriyo",
            "telegram_user_id": None,
            "enrollment_id": 321,
        }

    monkeypatch.setattr(identity_routes, "authenticate_account_password", unexpected_auth_v2)
    monkeypatch.setattr(identity_routes, "verify_student_credentials", fake_legacy_student)
    monkeypatch.setattr(identity_routes, "record_student_activity", lambda student_id: None)

    response = _post_login(client)

    assert response.status_code == 302
    assert response.headers["location"] == "/dashboard/321?school=sehriyo"
    assert calls == {"legacy": 1, "auth_v2": 0}


def test_account_auth_v2_flag_on_keeps_account_login_path_available(app, monkeypatch):
    import backend.domains.identity.routes as identity_routes

    client = _rate_limit_isolated_client(app, "account-login")
    calls = {"legacy": 0, "auth_v2": 0}
    _set_csrf_session(client)
    monkeypatch.setattr(identity_routes, "account_auth_v2_enabled", lambda: True)

    def unexpected_legacy(login, password):
        calls["legacy"] += 1
        raise AssertionError("Legacy auth must not run when ACCOUNT_AUTH_V2_ENABLED=1")

    def fake_auth_v2(login, password):
        calls["auth_v2"] += 1
        return _auth_v2_result(
            "student",
            auth_login="MSI00001",
            student_db_id=1001,
            student_id="MSI00001",
            student_full_name="Example Student",
            student_enrollment_id=321,
            student_school_code="sehriyo",
        )

    monkeypatch.setattr(identity_routes, "authenticate_account_password", fake_auth_v2)
    monkeypatch.setattr(identity_routes, "verify_student_credentials", unexpected_legacy)
    monkeypatch.setattr(identity_routes, "record_student_activity", lambda student_id: None)

    response = _post_login(client)

    assert response.status_code == 302
    assert response.headers["location"] == "/dashboard/321?school=sehriyo"
    assert calls == {"legacy": 0, "auth_v2": 1}


@pytest.mark.parametrize(
    "module_name",
    [
        "backend.api.v1",
        "backend.core",
        "backend.integrations",
        "backend.integrations.telegram",
        "backend.integrations.excel",
        "backend.integrations.storage",
    ],
)
def test_future_empty_packages_import_safely(module_name):
    module = importlib.import_module(module_name)

    assert module is not None
