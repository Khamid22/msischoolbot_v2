"""DB-5 academics, timetable and announcements domain migration coverage."""

from pathlib import Path


def test_academics_timetable_and_announcement_query_modules_import_successfully():
    import backend.modules.academics.repository as academic_queries
    import backend.modules.announcements.repository as announcement_queries
    import backend.modules.timetable.repository as timetable_queries

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
    assert callable(announcement_queries.list_announcement_rows)
    assert callable(announcement_queries.insert_announcement_row)
    assert callable(announcement_queries.update_announcement_row)


def test_announcement_legacy_query_wrapper_is_deleted_after_imports_migrate():
    active_backend_source = "\n".join(path.read_text() for path in Path("backend").rglob("*.py"))

    assert not Path("database/queries").exists()
    assert "database.queries.announcement_queries" not in active_backend_source


def test_academic_services_use_module_repositories():
    postgres_service_source = Path("backend/modules/academics/postgres_service.py").read_text()
    dashboard_service_source = Path("backend/modules/academics/internal_dashboard_service.py").read_text()
    announcement_service_source = Path("backend/modules/announcements/service.py").read_text()

    assert "from backend.modules.academics import repository as academic_repository" in postgres_service_source
    assert "from backend.modules.timetable import repository as timetable_repository" in postgres_service_source
    assert "academic_repository.list_curriculum_program_rows" in postgres_service_source
    assert "timetable_repository.list_schedule_rows" in postgres_service_source
    assert "timetable_repository.insert_lesson_session" in postgres_service_source
    assert "from backend.modules.academics import repository as academic_repository" in dashboard_service_source
    assert "academic_repository.list_internal_overview_enrollment_rows" in dashboard_service_source
    assert "academic_repository.get_enrollment_dashboard_row" in dashboard_service_source
    assert "from backend.modules.announcements import repository as announcement_repository" in announcement_service_source
    assert "announcement_repository.list_announcement_rows" in announcement_service_source


def test_targeted_academic_services_no_longer_embed_schema_sql():
    service_paths = [
        "backend/modules/academics/postgres_service.py",
        "backend/modules/academics/internal_dashboard_service.py",
        "backend/modules/announcements/service.py",
    ]
    for path in service_paths:
        source = Path(path).read_text()
        assert "conn.execute" not in source
        assert "FROM msi_v2" not in source
        assert "JOIN msi_v2" not in source
        assert "INSERT INTO msi_v2" not in source
        assert "UPDATE msi_v2" not in source
        assert "DELETE FROM msi_v2" not in source


def test_timetable_and_announcements_query_modules_use_migrated_schema():
    timetable_query_source = Path("backend/modules/timetable/repository.py").read_text()
    announcement_query_source = Path("backend/modules/announcements/repository.py").read_text()
    academic_query_source = Path("backend/modules/academics/repository.py").read_text()

    assert "FROM msi_v2.group_schedule_rules" in timetable_query_source
    assert "FROM msi_v2.lesson_sessions" in timetable_query_source
    assert "CREATE TABLE" not in announcement_query_source
    assert "FROM msi_v2.announcements" in announcement_query_source
    assert "FROM msi_v2.subject_programs" in academic_query_source
    assert "FROM msi_v2.group_students" in academic_query_source


def test_hod_teacher_academy_scope_sql_lives_in_module_repository():
    scope_source = Path("backend/modules/teacher_academy/permissions.py").read_text()
    academy_query_source = Path("backend/modules/teacher_academy/repository.py").read_text()

    assert "from backend.modules.teacher_academy import repository as academy_repository" in scope_source
    assert "from database import queries" not in scope_source
    assert "msi_v2." not in scope_source
    assert "list_hod_subject_scope_rows" in academy_query_source
    assert "get_academy_teacher_subject_id" in academy_query_source
    assert "get_assignment_subject_id" in academy_query_source
