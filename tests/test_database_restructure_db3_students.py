"""DB-3 student domain migration coverage."""

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


def test_student_identity_wrappers_still_export_domain_services():
    import backend.domains.students.service as student_service
    import backend.identity.passwords as legacy_passwords
    import backend.identity.profiles as legacy_profiles
    import backend.identity.student_accounts as legacy_student_accounts

    assert legacy_student_accounts.list_students_for_admin is student_service.list_students_for_admin
    assert legacy_student_accounts.record_student_activity is student_service.record_student_activity
    assert legacy_profiles.get_admin_student_profile is student_service.get_admin_student_profile
    assert legacy_profiles.get_dashboard_student_profile is student_service.get_dashboard_student_profile
    assert legacy_passwords.change_student_password is student_service.change_student_password
    assert legacy_passwords.admin_change_student_password is student_service.admin_change_student_password


def test_student_domain_imports_are_used_where_safe():
    dashboard_service_source = Path("backend/roles/student/services/dashboard_service.py").read_text()
    student_page_source = Path("backend/roles/student/routes/student_page.py").read_text()
    student_routes_source = Path("backend/roles/student/routes/students.py").read_text()
    admin_student_routes_source = Path("backend/roles/admin/routes/student_routes.py").read_text()
    admin_page_service_source = Path("backend/roles/admin/services/page_service.py").read_text()
    parent_service_source = Path("backend/domains/parents/service.py").read_text()
    office_hours_source = Path("backend/roles/student/routes/office_hours_routes.py").read_text()

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
        "backend/identity/student_accounts.py",
        "backend/identity/profiles.py",
        "backend/identity/passwords.py",
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
    office_hours_source = Path("backend/roles/student/routes/office_hours_routes.py").read_text()

    assert "resolve_sheet_student_for_admin" in route_service_source
    assert "list_public_dashboard_targets_for_student_row" not in route_service_source
    assert "legacy_public_dashboard_id" not in route_service_source
    assert "resolve_public_dashboard_for_student_row(student_row_id)" in parent_service_source
    assert "Compatibility wrapper for DB-3 student domain ownership" in academic_dashboard_source
    assert "legacy_public_dashboard_id" not in office_hours_source
    assert "connect_auth_db" not in office_hours_source
