from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def source(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_exception_migration_preserves_lesson_identity_and_audit_history():
    migration = source("database/alembic/versions/0010_lesson_schedule_exceptions.py")

    assert "lesson_session_id BIGINT NOT NULL" in migration
    assert "status IN ('cancelled', 'recovered')" in migration
    assert "original_session_date DATE NOT NULL" in migration
    assert "lesson_schedule_exceptions_one_active_per_lesson" in migration
    assert "DELETE FROM msi_v2.lesson_sessions" not in migration


def test_cancel_and_recover_reflow_existing_curriculum_session_ids():
    operations = source("backend/modules/academics/operations.py")

    assert "def cancel_lesson_session(" in operations
    assert "def recover_lesson_session(" in operations
    assert "Cancellation reason is required." in operations
    assert "schedule_curriculum_lesson(" in operations
    assert '"isCancellation": True' in operations
    assert '"canRecover": True' in operations


def test_both_management_roles_expose_cancel_and_recover_routes():
    admin = source("backend/internal_operations/academics_api.py")
    director = source("backend/workspaces/academic_director/academics_api.py")

    for route_source in (admin, director):
        assert '"/lessons/{lesson_session_id}/cancel"' in route_source
        assert '"/lessons/{lesson_session_id}/recover"' in route_source


def test_timetable_actions_and_validation_are_visible_in_the_ui():
    timetable = source("frontend/src/features/management/academic/Timetable.tsx")
    gradebook = source("frontend/src/features/management/academic/GroupGradebook.tsx")

    assert 'title="Cancel lesson"' in timetable
    assert 'title="Recover lesson"' in timetable
    assert 'title="Edit lesson content"' in timetable
    assert "Cancellation reason" in gradebook
    assert "Cancel & Move Forward" in gradebook
    assert "Recover & Restore" in gradebook
    assert 'lesson_name: lessonNameInput.trim()' in gradebook
