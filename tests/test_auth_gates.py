"""Authentication and same-origin gates, exercised without any database."""

XHR = {"X-Requested-With": "XMLHttpRequest"}


def test_unauthenticated_page_redirects_home(client):
    response = client.get("/dashboard/5")
    assert response.status_code == 302
    assert response.headers["location"] == "/"


def test_unauthenticated_api_returns_401_json(client):
    response = client.get("/api/students/5/dashboard", headers=XHR)
    assert response.status_code == 401
    assert response.json() == {"message": "Authentication required."}


def test_unauthenticated_admin_api_returns_401_json(client):
    response = client.get("/admin/api/complaints", headers=XHR)
    assert response.status_code == 401
    assert response.json() == {"message": "Authentication required."}


def test_teacher_page_redirects_without_session(client):
    # /teacher is public in the middleware; the router-level guard dependency
    # (GuardResponse) must bounce non-teachers to the portal home.
    response = client.get("/teacher")
    assert response.status_code == 302
    assert response.headers["location"] == "/"


def test_teacher_api_returns_guard_401_shape(client):
    response = client.get("/teacher/api/office-hours/availability", headers=XHR)
    assert response.status_code == 401
    body = response.json()
    assert body["ok"] is False
    assert "Teacher authentication required" in body["message"]


def test_cross_origin_post_rejected(client):
    response = client.post(
        "/login",
        data={"login": "x", "password": "y"},
        headers={"Origin": "https://evil.example"},
    )
    assert response.status_code == 403
    assert response.json() == {"message": "Cross-origin request rejected."}


def test_api_post_without_xhr_marker_rejected(client):
    response = client.post("/api/chat/messages", json={"body": "hi"})
    assert response.status_code == 403
    assert response.json() == {"message": "Cross-origin request rejected."}


def test_login_without_csrf_returns_400_html(client):
    response = client.post("/login", data={"login": "x", "password": "y"})
    assert response.status_code == 400
    assert response.headers["content-type"].startswith("text/html")
    assert "security token" in response.text
