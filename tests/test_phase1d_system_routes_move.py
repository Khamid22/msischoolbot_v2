import json
import os
from base64 import b64encode

from fastapi import FastAPI
from itsdangerous import TimestampSigner


def _session_secret():
    return (
        os.environ.get("APP_SECRET_KEY", os.environ.get("FLASK_SECRET_KEY", "")).strip()
        or "dev-only-insecure-key-do-not-use-in-prod"
    )


def _signed_session(data):
    encoded = b64encode(json.dumps(data).encode("utf-8"))
    return TimestampSigner(_session_secret()).sign(encoded).decode("utf-8")


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


def test_backend_server_app_still_starts():
    from backend.server import create_app

    app = create_app()

    assert isinstance(app, FastAPI)
    assert app.title == "MSI School API"


def test_system_routes_remain_registered(app):
    routes = _route_methods(app)

    assert "GET" in routes["/manifest.webmanifest"]
    assert "GET" in routes["/sw.js"]
    assert "GET" in routes["/api/v1/system/status"]
    assert "GET" in routes["/health/live"]
    assert "GET" in routes["/health/ready"]
    assert "GET" in routes["/api/v1/auth/me"]


def test_old_and_new_system_route_import_paths_work():
    import backend.application.system_page as legacy_system_routes
    import backend.modules.domains.identity.api as auth_routes
    import backend.application.system_api as system_routes

    assert legacy_system_routes.router is not None
    assert auth_routes.router is not None
    assert system_routes.router is not None
    assert legacy_system_routes.get_current_user is auth_routes.get_current_user
    assert legacy_system_routes.system_status is system_routes.system_status


def test_system_status_response_is_unchanged(client):
    response = client.get("/api/v1/system/status")

    assert response.status_code == 200
    assert response.json() == {
        "status": "success",
        "message": "MSI School Backend API is running and operational.",
    }


def test_liveness_does_not_require_database(client):
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["request_id"] == response.headers["x-request-id"]


def test_readiness_checks_database(client, monkeypatch):
    monkeypatch.setattr(
        "backend.application.system_api.check_database_ready",
        lambda **_kwargs: True,
    )

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["database"] == "ready"
    assert response.json()["request_id"] == response.headers["x-request-id"]


def test_readiness_fails_closed_when_database_is_unavailable(client, monkeypatch):
    def unavailable(**_kwargs):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr("backend.application.system_api.check_database_ready", unavailable)

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["request_id"] == response.headers["x-request-id"]


def test_auth_me_response_shape_is_unchanged(client):
    client.cookies.set(
        "session",
        _signed_session({"auth_role": "student", "auth_login": "MSI00001"}),
    )

    response = client.get("/api/v1/auth/me")
    payload = response.json()

    assert response.status_code == 200
    assert set(payload.keys()) == {"status", "data"}
    assert payload["status"] == "success"
    assert set(payload["data"].keys()) == {
        "account_id",
        "login",
        "role",
        "must_change_password",
        "session_version",
        "permissions",
    }
    assert payload["data"]["login"] == "MSI00001"
    assert payload["data"]["role"] == "student"
    assert isinstance(payload["data"]["permissions"], dict)
