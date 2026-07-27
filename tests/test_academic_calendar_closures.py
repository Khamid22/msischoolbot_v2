from datetime import date, time
from pathlib import Path

from backend.modules.domains.academics.calendar import service as calendar_closures
from backend.modules.domains.academics.gradebook.window import _gradebook_lesson_window
from backend.modules.domains.academics.calendar.scheduling import generate_teaching_dates


ROOT = Path(__file__).resolve().parents[1]


def source(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_teaching_date_generator_skips_overlapping_breaks_and_blocked_days():
    dates = generate_teaching_dates(
        start_date=date(2026, 6, 1),
        count=4,
        weekdays={0, 2, 4},
        blocked_dates={date(2026, 9, 2)},
        closures=[
            (date(2026, 6, 1), date(2026, 8, 31)),
            (date(2026, 8, 15), date(2026, 9, 1)),
        ],
    )

    assert dates == [
        date(2026, 9, 4),
        date(2026, 9, 7),
        date(2026, 9, 9),
        date(2026, 9, 11),
    ]


def test_school_reflow_validates_all_proposed_groups_as_one_transaction(monkeypatch):
    seen_exclusions = []

    def no_existing_conflicts(_conn, **kwargs):
        seen_exclusions.append(kwargs["excluded_session_ids"])
        return []

    monkeypatch.setattr(
        calendar_closures.calendar_repository,
        "list_reflow_occurrence_conflicts",
        no_existing_conflicts,
    )
    plans = [
        {
            "group": {"id": 11, "group_name": "AFT1"},
            "schedule": {"teacher_id": 7, "start_time": time(14), "end_time": time(15, 20)},
            "movable": [{"id": 101}],
            "dates": [date(2026, 9, 2)],
            "conflicts": [],
        },
        {
            "group": {"id": 12, "group_name": "AFT2"},
            "schedule": {"teacher_id": 7, "start_time": time(14), "end_time": time(15, 20)},
            "movable": [{"id": 202}],
            "dates": [date(2026, 9, 2)],
            "conflicts": [],
        },
    ]

    calendar_closures._validate_planned_occurrences(None, plans)

    assert seen_exclusions == [[101, 202], [101, 202]]
    assert plans[0]["conflicts"] == []
    assert "AFT2 overlaps with AFT1" in plans[1]["conflicts"][0]


def test_gradebook_months_keep_holidays_without_fake_cancellations():
    lessons = [
        {
            "id": 91,
            "date": "13/05/2026",
            "startTime": "14:00",
            "order": 91,
            "status": "completed",
            "isCancellation": False,
            "hasAcademicRecords": True,
        }
    ]
    closures = [
        {
            "title": "Summer holiday",
            "start_date": date(2026, 6, 1),
            "end_date": date(2026, 8, 31),
            "group_id": None,
        }
    ]

    selected, page = _gradebook_lesson_window(
        lessons,
        month="2026-07",
        closures=closures,
    )

    assert selected == []
    july = next(item for item in page["monthOptions"] if item["value"] == "2026-07")
    assert july["isLocked"] is True
    assert july["closureTitles"] == ["Summer holiday"]
    assert july["closureScopes"] == ["school"]
    assert july["protectedRecordCount"] == 0


def test_closure_migration_is_auditable_and_never_deletes_academic_records():
    migration = source("database/alembic/versions/0012_academic_calendar_closures.py")

    assert "CREATE TABLE msi_v2.academic_calendar_closures" in migration
    assert "school_id BIGINT NOT NULL" in migration
    assert "group_id BIGINT" in migration
    assert "start_date DATE NOT NULL" in migration
    assert "end_date DATE NOT NULL" in migration
    assert "created_by_staff_id" in migration
    assert "unlocked_by_staff_id" in migration
    assert "DELETE FROM msi_v2.lesson_sessions" not in migration
    assert "DELETE FROM msi_v2.attendance_records" not in migration


def test_academic_director_exposes_preview_create_list_and_unlock_routes():
    route_source = source("backend/modules/people/academic_director/workspace/academics_api.py")
    assert '"/calendar-closures"' in route_source
    assert '"/calendar-closures/preview"' in route_source
    assert '"/calendar-closures/{closure_id}/unlock"' in route_source
    assert "CalendarClosureConflictError" in route_source


def test_all_timetable_mutations_share_closure_aware_date_generation():
    service = source("backend/modules/domains/academics/timetable/service.py")
    operations = "\n".join(
        [
            source("backend/modules/domains/academics/timetable/operations.py"),
            source("backend/modules/domains/academics/lessons/service.py"),
        ]
    )
    closure_service = source("backend/modules/domains/academics/calendar/service.py")

    assert "generate_teaching_dates(" in service
    assert "list_effective_group_closures(" in service
    assert "group_date_has_active_closure(" in operations
    assert "Choose a teaching date outside the break" in operations
    assert "generate_teaching_dates(" in operations
    assert "lock_closure_scope" in closure_service
    assert "lock_group_timetable_for_reflow" in closure_service
    assert "conn.commit()" in closure_service


def test_closure_controls_are_visible_at_school_and_group_scope():
    modal = source("frontend/src/features/academics/timetable/CalendarClosuresModal.tsx")
    academic_timetable = source("frontend/src/features/academics/timetable/SchedulePanel.tsx")
    group_timetable = source("frontend/src/features/academics/timetable/ModernGroupTimetable.tsx")
    gradebook = source("frontend/src/features/academics/gradebook/GroupGradebook.tsx")

    assert "Manage Breaks" in academic_timetable
    assert ">Breaks</button>" in group_timetable
    assert "Inherited school lock" in modal
    assert "Jun–Aug" in modal
    assert "Rebuild future timetable" in modal
    assert 'option.hasClosure ? " — Holiday"' in gradebook
    assert "Recorded before holiday lock" in gradebook
