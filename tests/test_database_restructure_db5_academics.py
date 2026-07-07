"""DB-5 academics, timetable and announcements domain migration coverage."""

from pathlib import Path


def test_academics_timetable_and_announcement_query_modules_import_successfully():
    import backend.domains.academics.queries as academic_queries
    import backend.domains.announcements.queries as announcement_queries
    import backend.domains.timetable.queries as timetable_queries

    assert callable(academic_queries.list_subject_rows)
    assert callable(academic_queries.list_curriculum_program_rows)
    assert callable(academic_queries.list_curriculum_item_rows)
    assert callable(academic_queries.list_group_rows)
    assert callable(academic_queries.list_enrollment_rows)
    assert callable(academic_queries.list_internal_overview_enrollment_rows)
    assert callable(academic_queries.get_enrollment_dashboard_row)
    assert callable(timetable_queries.list_schedule_rows)
    assert callable(timetable_queries.list_session_rows)
    assert callable(timetable_queries.insert_schedule_rule)
    assert callable(announcement_queries.ensure_announcements_schema)
    assert callable(announcement_queries.list_announcement_rows)
    assert callable(announcement_queries.insert_announcement_row)
    assert callable(announcement_queries.update_announcement_row)


def test_announcement_legacy_query_wrapper_still_exports_domain_functions():
    import backend.domains.announcements.queries as announcement_queries
    import database.queries.announcement_queries as legacy_announcement_queries

    assert legacy_announcement_queries.ensure_announcements_schema is announcement_queries.ensure_announcements_schema
    assert legacy_announcement_queries.list_announcement_rows is announcement_queries.list_announcement_rows
    assert legacy_announcement_queries.insert_announcement_row is announcement_queries.insert_announcement_row


def test_academic_services_use_domain_query_modules():
    postgres_service_source = Path("backend/domains/academics/postgres_service.py").read_text()
    dashboard_service_source = Path("backend/domains/academics/internal_dashboard_service.py").read_text()
    announcement_service_source = Path("backend/domains/announcements/service.py").read_text()

    assert "from backend.domains.academics import queries as academic_queries" in postgres_service_source
    assert "from backend.domains.timetable import queries as timetable_queries" in postgres_service_source
    assert "academic_queries.list_curriculum_program_rows" in postgres_service_source
    assert "timetable_queries.list_schedule_rows" in postgres_service_source
    assert "timetable_queries.insert_lesson_session" in postgres_service_source
    assert "from backend.domains.academics import queries as academic_queries" in dashboard_service_source
    assert "academic_queries.list_internal_overview_enrollment_rows" in dashboard_service_source
    assert "academic_queries.get_enrollment_dashboard_row" in dashboard_service_source
    assert "from backend.domains.announcements import queries as announcement_queries" in announcement_service_source
    assert "announcement_queries.list_announcement_rows" in announcement_service_source


def test_targeted_academic_services_no_longer_embed_schema_sql():
    service_paths = [
        "backend/domains/academics/postgres_service.py",
        "backend/domains/academics/internal_dashboard_service.py",
        "backend/domains/announcements/service.py",
        "database/queries/announcement_queries.py",
    ]
    for path in service_paths:
        source = Path(path).read_text()
        assert "conn.execute" not in source
        assert "FROM msi_v2" not in source
        assert "JOIN msi_v2" not in source
        assert "INSERT INTO msi_v2" not in source
        assert "UPDATE msi_v2" not in source
        assert "DELETE FROM msi_v2" not in source


def test_timetable_and_announcements_query_modules_own_runtime_sql():
    timetable_query_source = Path("backend/domains/timetable/queries.py").read_text()
    announcement_query_source = Path("backend/domains/announcements/queries.py").read_text()
    academic_query_source = Path("backend/domains/academics/queries.py").read_text()

    assert "FROM msi_v2.group_schedule_rules" in timetable_query_source
    assert "FROM msi_v2.lesson_sessions" in timetable_query_source
    assert "CREATE TABLE IF NOT EXISTS msi_v2.announcements" in announcement_query_source
    assert "FROM msi_v2.announcements" in announcement_query_source
    assert "FROM msi_v2.subject_programs" in academic_query_source
    assert "FROM msi_v2.group_students" in academic_query_source


def test_hod_teacher_academy_scope_sql_lives_in_domain_queries():
    scope_source = Path("backend/roles/head_of_department/academy_scope.py").read_text()
    academy_query_source = Path("backend/domains/teacher_academy/queries.py").read_text()

    assert "from backend.domains.teacher_academy import queries as academy_queries" in scope_source
    assert "from database import queries" not in scope_source
    assert "msi_v2." not in scope_source
    assert "list_hod_subject_scope_rows" in academy_query_source
    assert "get_academy_teacher_subject_id" in academy_query_source
    assert "get_assignment_subject_id" in academy_query_source
