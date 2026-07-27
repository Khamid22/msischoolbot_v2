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
    operations = source("backend/modules/domains/academics/timetable/operations.py")
    read_service = source("backend/modules/domains/academics/groups/read_service.py")

    assert "def cancel_lesson_session(" in operations
    assert "def recover_lesson_session(" in operations
    assert "Cancellation reason is required." in operations
    assert "schedule_curriculum_lesson(" in operations
    assert '"is_cancellation": True' in read_service
    assert '"can_recover": True' in read_service


def test_academic_director_exposes_cancel_and_recover_routes():
    director = source("backend/modules/people/academic_director/workspace/academics_api.py")

    assert '"/lessons/{lesson_session_id}/cancel"' in director
    assert '"/lessons/{lesson_session_id}/recover"' in director


def test_timetable_actions_and_validation_are_visible_in_the_ui():
    timetable = source("frontend/src/features/academics/timetable/ModernGroupTimetable.tsx")

    assert "Cancel this lesson" in timetable
    assert "Recover Lesson" in timetable
    assert "Lesson details" in timetable
    assert "Cancellation reason" in timetable
    assert "Cancel & Move Forward" in timetable
    assert "allow_recorded_lesson_changes" in timetable


def test_range_payload_keeps_exceptions_separate_and_marks_recorded_lessons():
    repository = source("backend/modules/domains/academics/timetable/repository.py")
    read_service = source("backend/modules/domains/academics/groups/read_service.py")

    assert "def list_timetable_exceptions_in_range(" in repository
    assert "AS has_academic_records" in repository
    assert '"exceptions": exceptions' in read_service
    assert '"exception_key": f"lesson-exception:' in read_service
    assert '"hasAcademicRecords"' in read_service


def test_reflow_mutations_lock_rows_and_return_deltas_not_gradebook():
    repository = source("backend/modules/domains/academics/timetable/repository.py")
    operations = source("backend/modules/domains/academics/timetable/operations.py")
    director = source("backend/modules/people/academic_director/workspace/academics_api.py")

    assert "def lock_group_timetable_for_reflow(" in repository
    assert "ORDER BY id FOR UPDATE" in repository
    assert "allow_recorded_lesson_changes" in operations
    assert '"affectedIds": affected_ids' in operations
    cancel_block = director.split("def cancel_lesson", 1)[1].split("@router.post", 1)[0]
    assert "get_group_gradebook" not in cancel_block
    assert "AcademicConflictError" in cancel_block
