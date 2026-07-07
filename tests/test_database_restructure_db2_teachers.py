"""DB-2 teacher domain migration coverage."""

from pathlib import Path


def test_teacher_domain_modules_import_successfully():
    import backend.domains.teachers.queries as teacher_queries
    import backend.domains.teachers.service as teacher_service

    assert callable(teacher_queries.list_teachers_rows)
    assert callable(teacher_queries.get_teacher_by_id_row)
    assert callable(teacher_queries.get_teacher_login_row)
    assert callable(teacher_queries.insert_teacher_profile_row)
    assert callable(teacher_queries.upsert_teacher_subject)
    assert callable(teacher_service.list_teachers)
    assert callable(teacher_service.get_teacher_by_id)
    assert callable(teacher_service.upsert_teacher)
    assert teacher_service.queries is teacher_queries


def test_teacher_legacy_query_wrapper_still_exports_domain_functions():
    import backend.domains.teachers.queries as teacher_queries
    import database.queries.teacher_queries as legacy_teacher_queries

    assert legacy_teacher_queries.list_teachers_rows is teacher_queries.list_teachers_rows
    assert legacy_teacher_queries.get_teacher_by_id_row is teacher_queries.get_teacher_by_id_row
    assert legacy_teacher_queries.get_next_teacher_code is teacher_queries.get_next_teacher_code
    assert legacy_teacher_queries.upsert_teacher_subject is teacher_queries.upsert_teacher_subject


def test_teacher_identity_wrapper_still_exports_domain_services():
    import backend.domains.teachers.service as teacher_service
    import backend.identity.teachers as legacy_teacher_service

    assert legacy_teacher_service.list_teachers is teacher_service.list_teachers
    assert legacy_teacher_service.get_teacher_by_id is teacher_service.get_teacher_by_id
    assert legacy_teacher_service.upsert_teacher is teacher_service.upsert_teacher
    assert legacy_teacher_service.subject_teacher_login_prefix is teacher_service.subject_teacher_login_prefix


def test_teacher_domain_imports_are_used_where_safe():
    teacher_role_source = Path("backend/roles/teacher/services.py").read_text()
    academy_service_source = Path("backend/domains/teacher_academy/service.py").read_text()
    academy_api_source = Path("backend/api/v1/teacher_academy_actions.py").read_text()
    admin_teacher_routes_source = Path("backend/roles/admin/routes/teacher_routes.py").read_text()
    admin_page_service_source = Path("backend/roles/admin/services/page_service.py").read_text()

    assert "from backend.domains.teachers.service import" in teacher_role_source
    assert "from backend.domains.teachers.service import list_teachers, upsert_teacher" in academy_service_source
    assert "from backend.domains.teachers.service import list_teachers" in academy_api_source
    assert "from backend.domains.teachers.service import (" in admin_teacher_routes_source
    assert "from backend.domains.teachers.service import list_teachers" in admin_page_service_source


def test_teacher_academy_domain_uses_teacher_domain_queries_for_teacher_helpers():
    source = Path("backend/domains/teacher_academy/queries.py").read_text()

    assert "from backend.domains.teachers import queries as teacher_queries" in source
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
        assert f"{helper_name} = teacher_queries.{helper_name}" in source


def test_legacy_teacher_query_file_is_only_a_compatibility_wrapper():
    source = Path("database/queries/teacher_queries.py").read_text()

    assert "backend.domains.teachers.queries" in source
    assert "def list_teachers_rows" not in source
    assert "FROM msi_v2" not in source
    assert "INSERT INTO msi_v2" not in source
    assert "UPDATE msi_v2" not in source
