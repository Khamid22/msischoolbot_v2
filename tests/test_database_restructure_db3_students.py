"""DB-3 student domain migration coverage."""

import pytest

from pathlib import Path


def test_student_domain_modules_import_successfully():
    import backend.domains.students.queries as student_queries
    import backend.domains.students.service as student_service

    assert callable(student_queries.get_student_login_row)
    assert callable(student_queries.get_students_sheet_map_row)
    assert callable(student_queries.get_student_admin_row)
    assert callable(student_queries.list_public_dashboard_targets_for_student_row)
    assert callable(student_queries.get_student_ref_by_public_dashboard_id)
    assert callable(student_queries.get_student_ref_by_public_dashboard_id_and_school)
    assert callable(student_queries.list_active_subject_options_for_student)
    assert callable(student_service.get_admin_student_profile)
    assert callable(student_service.get_dashboard_student_profile)
    assert callable(student_service.get_student_db_id_by_enrollment_id)
    assert callable(student_service.get_student_subject_enrollments)
    assert callable(student_service.list_enrolled_subject_options)
    assert callable(student_service.resolve_public_dashboard_for_student_row)
    assert student_service.queries is student_queries


def test_student_legacy_query_wrapper_still_exports_domain_functions():
    import backend.domains.students.queries as student_queries
    import database.cross_queries.student_queries as legacy_student_queries

    assert legacy_student_queries.get_student_login_row is student_queries.get_student_login_row
    assert legacy_student_queries.get_students_sheet_map_row is student_queries.get_students_sheet_map_row
    assert legacy_student_queries.get_student_admin_row is student_queries.get_student_admin_row
    assert legacy_student_queries.get_student_by_telegram_id is student_queries.get_student_by_telegram_id


def test_student_identity_wrappers_are_gone():
    for module_name in (
        "backend.identity.passwords",
        "backend.identity.profiles",
        "backend.identity.student_accounts",
    ):
        with pytest.raises(ModuleNotFoundError):
            __import__(module_name)


def test_student_domain_imports_are_used_where_safe():
    dashboard_service_source = Path("backend/roles/student/services/dashboard_service.py").read_text()
    student_page_source = Path("backend/pages/student.py").read_text()
    student_routes_source = Path("backend/pages/student_forms.py").read_text()
    admin_student_routes_source = Path("backend/roles/admin/routes/student_routes.py").read_text()
    admin_page_service_source = Path("backend/roles/admin/services/page_service.py").read_text()
    parent_service_source = Path("backend/domains/parents/service.py").read_text()
    office_hours_source = Path("backend/pages/student_office_hours.py").read_text()

    assert "from backend.domains.students.service import (" in dashboard_service_source
    assert "from backend.domains.students.service import (" in student_page_source
    assert "from backend.domains.students.service import change_student_password" in student_routes_source
    assert "from backend.domains.students.service import (" in admin_student_routes_source
    assert "from backend.domains.students.service import get_admin_student_profile, list_students_for_admin" in admin_page_service_source
    assert "from backend.domains.students.service import resolve_public_dashboard_for_student_row" in parent_service_source
    assert "from backend.domains.students.service import list_enrolled_subject_options" in office_hours_source
    assert "from backend.domains.teachers.service import list_teachers" in office_hours_source


def test_student_legacy_files_are_only_compatibility_wrappers():
    wrapper_paths = [
        "database/cross_queries/student_queries.py",
    ]
    for path in wrapper_paths:
        source = Path(path).read_text()
        assert "backend.domains.students" in source
        assert "FROM msi_v2" not in source
        assert "JOIN msi_v2" not in source
        assert "UPDATE msi_v2" not in source
        assert "INSERT INTO msi_v2" not in source


def test_student_public_dashboard_resolution_uses_student_domain():
    route_service_source = Path("backend/roles/admin/services/route_service.py").read_text()
    parent_service_source = Path("backend/domains/parents/service.py").read_text()
    academic_dashboard_source = Path("backend/domains/academics/internal_dashboard_service.py").read_text()
    office_hours_source = Path("backend/pages/student_office_hours.py").read_text()

    assert "resolve_sheet_student_for_admin" in route_service_source
    assert "list_public_dashboard_targets_for_student_row" not in route_service_source
    assert "legacy_public_dashboard_id" not in route_service_source
    assert "resolve_public_dashboard_for_student_row(student_row_id)" in parent_service_source
    assert "Compatibility wrapper for DB-3 student domain ownership" in academic_dashboard_source
    assert "legacy_public_dashboard_id" not in office_hours_source
    assert "connect_auth_db" not in office_hours_source


def test_direct_dashboard_lookup_allows_public_dashboard_without_legacy_enrollment():
    academic_queries_source = Path("backend/domains/academics/queries.py").read_text()
    dashboard_lookup_source = academic_queries_source.split("def get_enrollment_dashboard_row", 1)[1].split(
        "\ndef list_enrollment_attendance_rows",
        1,
    )[0]

    assert "COALESCE(\n                   gs.legacy_enrollment_id" in dashboard_lookup_source
    assert "gs.legacy_enrollment_id IS NOT NULL" not in dashboard_lookup_source


def test_student_public_dashboard_resolution_uses_canonical_subject_order(monkeypatch):
    from backend.domains.students import service as student_service

    class NullConnection:
        def __enter__(self):
            return object()

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr(student_service, "_connect", lambda: NullConnection())
    monkeypatch.setattr(
        student_service.queries,
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
