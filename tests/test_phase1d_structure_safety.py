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


def _account_auth_result(role, *, account_role=None, **session_overrides):
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


def test_account_login_path_is_always_available(app, monkeypatch):
    import backend.pages.portal.home as identity_routes

    client = _rate_limit_isolated_client(app, "account-login")
    calls = {"auth": 0}
    _set_csrf_session(client)

    def fake_account_auth(login, password):
        calls["auth"] += 1
        return _account_auth_result(
            "student",
            auth_login="MSI00001",
            student_db_id=1001,
            student_id="MSI00001",
            student_full_name="Example Student",
            student_enrollment_id=321,
            student_school_code="sehriyo",
        )

    monkeypatch.setattr(identity_routes, "authenticate_account_password", fake_account_auth)
    monkeypatch.setattr(identity_routes, "record_student_activity", lambda student_id: None)

    response = _post_login(client)

    assert response.status_code == 302
    assert response.headers["location"] == "/dashboard/321?school=sehriyo"
    assert calls == {"auth": 1}


@pytest.mark.parametrize(
    "module_name",
    [
        "backend.api.v1",
        "backend.pages",
        "backend.schemas",
        "backend.services",
        "backend.repositories",
        "backend.core",
        "backend.integrations",
        "backend.integrations.telegram",
        "backend.integrations.storage",
    ],
)
def test_future_empty_packages_import_safely(module_name):
    module = importlib.import_module(module_name)

    assert module is not None
