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


def test_teacher_cancel_availability_scopes_to_current_teacher(client, monkeypatch):
    import backend.roles.teacher.routes as teacher_routes

    calls = {}
    monkeypatch.setattr(teacher_routes, "current_auth_role", lambda: "teacher")
    monkeypatch.setattr(teacher_routes, "current_teacher_id", lambda: 42)

    def fake_cancel(availability_id, *, teacher_id=None):
        calls["availability_id"] = availability_id
        calls["teacher_id"] = teacher_id

    monkeypatch.setattr(teacher_routes.oh_service, "cancel_availability", fake_cancel)

    response = client.patch(
        "/teacher/api/office-hours/availability/7",
        json={"status": "cancelled"},
        headers=XHR,
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert calls == {"availability_id": 7, "teacher_id": 42}


def test_teacher_update_booking_status_scopes_to_current_teacher(client, monkeypatch):
    import backend.roles.teacher.routes as teacher_routes

    calls = {}
    monkeypatch.setattr(teacher_routes, "current_auth_role", lambda: "teacher")
    monkeypatch.setattr(teacher_routes, "current_teacher_id", lambda: 42)

    def fake_update(booking_id, status, teacher_note, *, teacher_id=None):
        calls["booking_id"] = booking_id
        calls["status"] = status
        calls["teacher_note"] = teacher_note
        calls["teacher_id"] = teacher_id

    monkeypatch.setattr(teacher_routes.oh_service, "update_booking_status", fake_update)

    response = client.patch(
        "/teacher/api/office-hours/bookings/11",
        json={"status": "completed", "teacher_note": "Done"},
        headers=XHR,
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert calls == {
        "booking_id": 11,
        "status": "completed",
        "teacher_note": "Done",
        "teacher_id": 42,
    }


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
