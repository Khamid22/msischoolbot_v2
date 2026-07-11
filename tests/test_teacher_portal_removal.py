"""Teacher remains staff data but no longer has an LMS portal."""

from pathlib import Path

from backend.core.access.roles import is_valid_role, normalize_role
from backend.modules.accounts import service as accounts


def test_teacher_is_normalizable_staff_data_but_not_a_session_role():
    assert normalize_role("teacher") == "teacher"
    assert is_valid_role("teacher") is False
    assert "teacher" not in accounts.ACCOUNT_AUTH_ROLES


def test_teacher_portal_files_and_frontend_page_are_removed():
    assert not Path("backend/workspaces/teacher").exists()
    assert not Path("backend/pages/teachers").exists()
    assert not Path("backend/api/v1/teachers").exists()
    assert not Path("frontend/src/workspaces/teacher").exists()
    assert "teacher-home" not in Path("frontend/src/app/App.tsx").read_text()


def test_teacher_staff_and_academy_modules_are_preserved():
    for path in [
        Path("backend/modules/staff_records/teachers_service.py"),
        Path("backend/modules/staff_records/teachers_repository.py"),
        Path("backend/modules/staff_records/development_service.py"),
        Path("backend/modules/staff_records/development_repository.py"),
    ]:
        assert path.exists()


def test_teacher_accounts_are_disabled_by_migration():
    source = Path(
        "database/alembic/versions/0008_remove_teacher_portal_access.py"
    ).read_text()
    assert "WHERE role = 'teacher'" in source
    assert "status = 'disabled'" in source
    assert "session_version = session_version + 1" in source


def test_teacher_page_and_api_routes_are_absent(app):
    route_pairs = {
        (method, route.path)
        for route in app.routes
        for method in getattr(route, "methods", set())
    }
    assert ("GET", "/teacher") not in route_pairs
    assert not any(path.startswith("/api/v1/teacher/") for _, path in route_pairs)
