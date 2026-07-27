from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_group_timetable_schedules_existing_curriculum_lessons():
    service = (ROOT / "backend/modules/domains/academics/timetable/service.py").read_text(encoding="utf-8")
    repository = (ROOT / "backend/modules/domains/academics/timetable/repository.py").read_text(encoding="utf-8")

    assert "def schedule_group_curriculum(" in service
    assert 'scope not in {"all", "from_date", "remaining"}' in service
    assert "schedule_curriculum_lesson(" in service
    assert "UPDATE msi_v2.lesson_sessions SET schedule_rule_id=" in repository
    assert "program_item_id IS NULL" in repository


def test_group_ui_owns_setup_in_timetable_and_dates_are_read_only():
    panel = (ROOT / "frontend/src/features/academics/gradebook/GroupGradebook.tsx").read_text(encoding="utf-8")
    timetable = (ROOT / "frontend/src/features/academics/timetable/ModernGroupTimetable.tsx").read_text(encoding="utf-8")
    groups = (ROOT / "frontend/src/features/academics/AcademicPanel.tsx").read_text(encoding="utf-8")

    assert "Set Up Timetable" in timetable
    assert "Configure" in timetable
    assert "Select timetable month" in timetable
    assert timetable.index('aria-label="Previous period"') < timetable.index('(["agenda", "calendar"]')
    assert "+ New Student" not in panel  # icon and label are separate JSX nodes
    assert "New Student</button>" not in panel
    assert "Add student</button>" in panel
    assert "hasExistingTimetable()" in panel
    assert "Entire timetable history" in panel
    assert "Lessons from a specific date" in panel
    assert "Future unrecorded lessons" in panel
    assert "allow_recorded_lesson_changes" in panel
    assert "change_course_launch_date" in panel
    assert 'title="Date supplied by the timetable"' in panel
    assert 'asString(group.setup_status) === "new"' in groups


def test_modern_timetable_opens_on_today_and_fetches_only_the_visible_range():
    source = (ROOT / "frontend/src/features/academics/timetable/ModernGroupTimetable.tsx").read_text(encoding="utf-8")

    assert "useState(schoolTodayKey)" in source
    assert "academicManagementGroupTimetableApi" in source
    assert 'queryKey: ["academic", "timetable", groupId, range.from, range.to]' in source
    assert 'type PrimaryMode = "agenda" | "calendar"' in source
    assert 'type CalendarMode = "week" | "month"' in source
