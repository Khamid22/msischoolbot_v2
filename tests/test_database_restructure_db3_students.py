"""DB-3 student domain migration coverage."""

import pytest

from pathlib import Path


def test_student_domain_modules_import_successfully():
    import backend.modules.domains.student_records.repository as student_repository
    import backend.modules.domains.student_records.service as student_service

    assert not hasattr(student_repository, "get_student_login_row")
    assert callable(student_repository.get_student_enrollment_map_row)
    assert callable(student_repository.get_student_dashboard_row_by_id)
    assert callable(student_repository.list_public_dashboard_targets_for_student_row)
    assert callable(student_repository.get_student_ref_by_public_dashboard_id)
    assert callable(student_repository.get_student_ref_by_public_dashboard_id_and_school)
    assert callable(student_repository.list_active_subject_options_for_student)
    assert callable(student_service.get_dashboard_student_profile)
    assert callable(student_service.get_student_db_id_by_enrollment_id)
    assert callable(student_service.get_student_subject_enrollments)
    assert callable(student_service.list_enrolled_subject_options)
    assert callable(student_service.resolve_public_dashboard_for_student_row)
    assert student_service.repository is student_repository


def test_student_legacy_query_wrapper_is_gone():
    assert not Path("database/cross_queries/student_repository.py").exists()
    with pytest.raises(ModuleNotFoundError):
        __import__("database.cross_queries.student_repository")


def test_student_identity_wrappers_are_gone():
    for module_name in (
        "backend.identity.passwords",
        "backend.identity.profiles",
        "backend.identity.student_accounts",
    ):
        with pytest.raises(ModuleNotFoundError):
            __import__(module_name)


def test_student_domain_imports_are_used_where_safe():
    dashboard_service_source = Path("backend/modules/people/student/dashboard.py").read_text()
    student_page_source = Path("backend/modules/people/student/workspace/page.py").read_text()
    student_routes_source = Path("backend/modules/people/student/workspace/forms.py").read_text()
    auth_routes_source = Path("backend/modules/domains/identity/api.py").read_text()
    parent_service_source = Path("backend/modules/domains/parent_relationships/service.py").read_text()
    office_hours_source = Path("backend/modules/people/student/workspace/office_hours.py").read_text()

    assert "from backend.modules.domains.student_records.contracts" in dashboard_service_source
    assert "from backend.modules.people.student.contracts import (" in student_page_source
    assert "change_student_password" not in student_routes_source
    assert "from backend.modules.domains.identity.service import change_own_password" in auth_routes_source
    assert not Path("backend/internal_operations").exists()
    assert "from backend.modules.domains.student_records.contracts import (" in parent_service_source
    assert "from backend.modules.people.student.contracts import (" in office_hours_source
    assert "list_enrolled_subject_options" in office_hours_source
    assert "list_teachers" in office_hours_source


def test_student_query_sql_is_owned_by_the_domain():
    source = Path("backend/modules/domains/student_records/repository.py").read_text()

    assert "def get_student_enrollment_map_row" in source
    assert "FROM msi_v2" in source


def test_student_public_dashboard_resolution_uses_student_domain():
    parent_service_source = Path("backend/modules/domains/parent_relationships/service.py").read_text()
    academic_dashboard_source = Path("backend/modules/domains/reporting/academic_dashboard.py").read_text()
    office_hours_source = Path("backend/modules/people/student/workspace/office_hours.py").read_text()

    assert "resolve_public_dashboard_for_student_row(student_row_id)" in parent_service_source
    assert "canonical PostgreSQL academic tables" in academic_dashboard_source
    assert "legacy_public_dashboard_id" not in office_hours_source
    assert "connect_auth_db" not in office_hours_source


def test_direct_dashboard_lookup_allows_public_dashboard_without_legacy_enrollment():
    academic_queries_source = Path("backend/modules/domains/reporting/academic_repository.py").read_text()
    dashboard_lookup_source = academic_queries_source.split("def get_enrollment_dashboard_row", 1)[1].split(
        "\ndef list_enrollment_attendance_rows",
        1,
    )[0]

    assert "COALESCE(\n                   gs.legacy_enrollment_id" in dashboard_lookup_source
    assert "gs.legacy_enrollment_id IS NOT NULL" not in dashboard_lookup_source


def test_student_public_dashboard_resolution_uses_canonical_subject_order(monkeypatch):
    from backend.modules.domains.student_records import service as student_service

    class NullConnection:
        def __enter__(self):
            return object()

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr(student_service, "_connect", lambda: NullConnection())
    monkeypatch.setattr(
        student_service.repository,
        "list_public_dashboard_targets_for_student_row",
        lambda _conn, _student_row_id: [
            {
                "public_dashboard_id": 12846656148,
                "subject_name": "English as a Second Language",
                "group_name": "MG1",
                "school_key": "school5",
            },
            {
                "public_dashboard_id": 1471265890,
                "subject_name": "IGCSE Mathematics A",
                "group_name": "MG1",
                "school_key": "school5",
            },
        ],
    )

    resolved = student_service.resolve_public_dashboard_for_student_row(
        2,
        preferred_group="MG1",
        school_code="school5",
    )

    assert resolved == {
        "student_id": 1471265890,
        "subject": "IGCSE Mathematics A",
        "group": "MG1",
        "school": "school5",
    }
