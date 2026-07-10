"""DB-2 teacher domain migration coverage."""

import pytest

from pathlib import Path


def test_teacher_module_imports_successfully():
    import backend.repositories.teachers as teacher_repository
    import backend.services.teachers.core as teacher_service

    assert callable(teacher_repository.list_teachers_rows)
    assert callable(teacher_repository.get_teacher_by_id_row)
    assert callable(teacher_repository.get_teacher_login_row)
    assert callable(teacher_repository.insert_teacher_profile_row)
    assert callable(teacher_repository.upsert_teacher_subject)
    assert callable(teacher_service.list_teachers)
    assert callable(teacher_service.get_teacher_by_id)
    assert callable(teacher_service.upsert_teacher)
    assert teacher_service.repository is teacher_repository


def test_teacher_legacy_query_wrapper_is_gone():
    assert not Path("database/queries/teacher_queries.py").exists()
    with pytest.raises(ModuleNotFoundError):
        __import__("database.queries.teacher_queries")


def test_teacher_identity_wrapper_is_gone():
    with pytest.raises(ModuleNotFoundError):
        import backend.identity.teachers  # noqa: F401


def test_teacher_module_service_is_used_by_consumers():
    teacher_workspace_source = Path("backend/services/teachers/workspace.py").read_text()
    academy_service_source = Path("backend/services/teacher_academy/core.py").read_text()
    academy_api_source = Path("backend/services/teacher_academy/http_responses.py").read_text()
    admin_teacher_routes_source = Path("backend/pages/teachers/admin_forms.py").read_text()
    admin_page_service_source = Path("backend/services/admin/workspace.py").read_text()

    assert "from backend.services.teachers.core import" in teacher_workspace_source
    assert "from backend.services.teachers.core import list_teachers, upsert_teacher" in academy_service_source
    assert "from backend.services.teachers.core import list_teachers" in academy_api_source
    assert "from backend.services.teachers.core import (" in admin_teacher_routes_source
    assert "from backend.services.teachers.core import list_teachers" in admin_page_service_source


def test_teacher_academy_uses_teacher_repository_for_teacher_helpers():
    source = Path("backend/repositories/teacher_academy.py").read_text()

    assert "from backend.repositories import teachers as teacher_repository" in source
    for helper_name in [
        "get_teacher_by_full_name_row",
        "insert_teacher_profile_row",
        "upsert_teacher_subject",
        "get_teacher_auth_row_by_id",
        "get_next_teacher_code",
        "insert_teacher_auth",
        "activate_teacher_profile",
        "set_teacher_group_assignment",
    ]:
        assert f"{helper_name} = teacher_repository.{helper_name}" in source


def test_teacher_sql_is_owned_by_the_module_repository():
    source = Path("backend/repositories/teachers.py").read_text()

    assert "def list_teachers_rows" in source
    assert "FROM msi_v2" in source


def test_scattered_teacher_owners_are_removed():
    for path in [
        Path("backend/api/v1/teacher"),
        Path("backend/pages/teacher.py"),
        Path("backend/domains/teachers"),
        Path("backend/roles/teacher"),
    ]:
        assert not path.exists(), f"Teacher ownership must stay in the teacher layer files: {path}"
    assert Path("backend/pages/teachers/home.py").is_file()
    assert Path("backend/repositories/teachers.py").is_file()
