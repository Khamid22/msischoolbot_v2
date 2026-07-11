from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_group_timetable_schedules_existing_curriculum_lessons():
    service = (ROOT / "backend/modules/academics/service.py").read_text(encoding="utf-8")
    repository = (ROOT / "backend/modules/academics/timetable_repository.py").read_text(encoding="utf-8")

    assert "def schedule_group_curriculum(" in service
    assert 'scope not in {"all", "from_date", "remaining"}' in service
    assert "schedule_curriculum_lesson(" in service
    assert "UPDATE msi_v2.lesson_sessions SET schedule_rule_id=" in repository
    assert "program_item_id IS NULL" in repository


def test_group_ui_owns_setup_in_timetable_and_dates_are_read_only():
    panel = (ROOT / "frontend/src/features/management/academic/GroupGradebook.tsx").read_text(encoding="utf-8")
    groups = (ROOT / "frontend/src/features/management/AcademicPanel.tsx").read_text(encoding="utf-8")

    assert "Set Up Timetable" in panel
    assert "Change Schedule" in panel
    assert 'title="Date supplied by the timetable"' in panel
    assert 'asString(group.setup_status) === "new"' in groups


def test_timetable_opens_on_first_scheduled_lesson():
    source = (ROOT / "frontend/src/features/management/academic/Timetable.tsx").read_text(encoding="utf-8")

    assert "firstScheduledIso" in source
    assert "setCursor(firstLessonDate)" in source
    assert "Scheduled program lessons" in source
