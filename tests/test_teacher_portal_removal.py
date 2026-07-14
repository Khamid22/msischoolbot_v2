"""Teacher identity remains domain-owned and exposes a read-only workspace."""

from pathlib import Path

from backend.core.access.roles import is_valid_role, normalize_role
from backend.modules.identity import service as accounts


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
