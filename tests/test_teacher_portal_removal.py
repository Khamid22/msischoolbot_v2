"""Teacher identity remains domain-owned and exposes a read-only workspace."""

import json
import os
from base64 import b64encode
from pathlib import Path

from itsdangerous import TimestampSigner

from backend.core.access.roles import is_valid_role, normalize_role
from backend.modules.identity import service as accounts


def _set_teacher_session(client):
    secret = (
        os.environ.get("APP_SECRET_KEY", os.environ.get("FLASK_SECRET_KEY", "")).strip()
        or "dev-only-insecure-key-do-not-use-in-prod"
    )
    payload = {
        "auth_role": "teacher",
        "auth_login": "TCH0001",
        "teacher_id": 10,
        "staff_id": 2,
    }
    encoded = b64encode(json.dumps(payload).encode("utf-8"))
    client.cookies.set("session", TimestampSigner(secret).sign(encoded).decode("utf-8"))


def test_teacher_is_a_valid_session_role():
    assert normalize_role("teacher") == "teacher"
    assert is_valid_role("teacher") is True
    assert "teacher" in accounts.ACCOUNT_AUTH_ROLES


def test_teacher_portal_is_a_read_only_workspace_adapter():
    assert Path("backend/workspaces/teacher/page.py").exists()
    assert not Path("backend/pages/teachers").exists()
    assert not Path("backend/api/v1/teachers").exists()
    assert Path("frontend/src/workspaces/teacher/pages/Home.tsx").exists()
    assert "teacher-home" in Path("frontend/src/app/App.tsx").read_text()
    assert "@router.post" not in Path("backend/workspaces/teacher/page.py").read_text()


def test_teacher_staff_and_academy_modules_are_preserved():
    for path in [
        Path("backend/modules/people/teachers/service.py"),
        Path("backend/modules/people/teachers/repository.py"),
        Path("backend/modules/teacher_academy/service.py"),
        Path("backend/modules/teacher_academy/repository.py"),
    ]:
        assert path.exists()


def test_teacher_accounts_are_disabled_by_migration():
    source = Path(
        "database/alembic/versions/0008_remove_teacher_portal_access.py"
    ).read_text()
    assert "WHERE role = 'teacher'" in source
    assert "status = 'disabled'" in source
    assert "session_version = session_version + 1" in source


def test_teacher_page_exists_without_teacher_mutation_api(app):
    route_pairs = set()

    def collect(routes):
        for route in routes:
            if type(route).__name__ == "_IncludedRouter":
                collect(route.original_router.routes)
                continue
            route_pairs.update(
                (method, route.path) for method in getattr(route, "methods", set())
            )

    collect(app.routes)
    assert ("GET", "/teacher") in route_pairs
    assert not any(path.startswith("/api/v1/teacher/") for _, path in route_pairs)


def test_teacher_page_renders_teacher_bootstrap_when_academy_profile_is_missing(client, monkeypatch):
    import backend.workspaces.teacher.page as teacher_page

    _set_teacher_session(client)
    monkeypatch.setattr(teacher_page, "_safe_teacher_academy_profile", lambda: None)

    response = client.get("/teacher")

    assert response.status_code == 200
    assert 'data-react-page="teacher-home"' in response.text
    assert '"page":"teacher-home"' in response.text
    assert 'data-react-page="student-not-found"' not in response.text
