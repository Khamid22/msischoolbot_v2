"""Authentication and same-origin gates, exercised without any database."""

import json
import os
from base64 import b64encode

from itsdangerous import TimestampSigner

XHR = {"X-Requested-With": "XMLHttpRequest"}


def _session_secret():
    return (
        os.environ.get("APP_SECRET_KEY", os.environ.get("FLASK_SECRET_KEY", "")).strip()
        or "dev-only-insecure-key-do-not-use-in-prod"
    )


def _set_session(client, data):
    encoded = b64encode(json.dumps(data).encode("utf-8"))
    client.cookies.set("session", TimestampSigner(_session_secret()).sign(encoded).decode("utf-8"))


def test_unauthenticated_page_redirects_home(client):
    response = client.get("/dashboard/5")
    assert response.status_code == 302
    assert response.headers["location"] == "/"


def test_unauthenticated_api_returns_401_json(client):
    response = client.get("/api/v1/student/office-hours/bookings", headers=XHR)
    assert response.status_code == 401
    assert response.json() == {"status": "error", "message": "Authentication required."}


def test_unauthenticated_admin_api_returns_401_json(client):
    response = client.get("/api/v1/admin/complaints", headers=XHR)
    assert response.status_code == 401
    assert response.json() == {"status": "error", "message": "Authentication required."}


def test_removed_teacher_page_redirects_logged_out_visitors_to_login(client):
    response = client.get("/teacher")
    assert response.status_code == 302
    assert response.headers["location"] == "/"


def test_removed_teacher_api_requires_session_before_route_resolution(client):
    response = client.get("/api/v1/teacher/office-hours/availability", headers=XHR)
    assert response.status_code == 401
    assert response.json() == {"status": "error", "message": "Authentication required."}


def test_removed_teacher_api_is_not_registered_for_other_roles(client):
    _set_session(client, {"auth_role": "student", "auth_login": "MSI00001"})
    response = client.get("/api/v1/teacher/office-hours/availability", headers=XHR)
    assert response.status_code == 404


def test_teacher_session_role_is_recognized(client):
    _set_session(client, {"auth_role": "teacher", "auth_login": "TCH0001", "teacher_id": 42})
    response = client.get("/api/v1/auth/me", headers=XHR)
    assert response.status_code == 200
    assert response.json()["data"]["role"] == "teacher"


def test_cross_origin_post_rejected(client):
    response = client.post(
        "/login",
        data={"login": "x", "password": "y"},
        headers={"Origin": "https://evil.example"},
    )
    assert response.status_code == 403
    assert response.json() == {"status": "error", "message": "Cross-origin request rejected."}


def test_api_post_without_xhr_marker_rejected(client):
    response = client.post("/api/v1/student/chat/messages", json={"body": "hi"})
    assert response.status_code == 403
    assert response.json() == {"status": "error", "message": "Cross-origin request rejected."}


def test_login_without_csrf_returns_400_html(client):
    response = client.post("/login", data={"login": "x", "password": "y"})
    assert response.status_code == 400
    assert response.headers["content-type"].startswith("text/html")
    assert "security token" in response.text
