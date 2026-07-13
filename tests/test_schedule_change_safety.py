from datetime import date

import pytest

from backend.modules.academics.service import (
    _resolve_course_launch_date,
    _select_schedule_change_lessons,
)


def lesson(identifier, *, status="scheduled", session_date=None, recorded=False):
    return {
        "id": identifier,
        "status": status,
        "session_date": session_date,
        "has_academic_records": recorded,
    }


def test_remaining_scope_never_moves_completed_or_recorded_lessons():
    lessons = [
        lesson(1, status="completed", session_date=date(2026, 7, 6)),
        lesson(2, session_date=date(2026, 7, 8), recorded=True),
        lesson(3, session_date=date(2026, 7, 15)),
        lesson(4),
    ]

    selected, anchor, protected_count, moved_count = _select_schedule_change_lessons(
        lessons,
        scope="remaining",
        effective_date=None,
        launch_date=date(2025, 10, 10),
        today=date(2026, 7, 13),
    )

    assert [row["id"] for row in selected] == [3, 4]
    assert anchor == date(2026, 7, 15)
    assert protected_count == 2
    assert moved_count == 0


def test_existing_course_launch_date_is_immutable_without_explicit_change():
    existing = {"start_date": date(2025, 10, 10)}

    assert _resolve_course_launch_date(
        existing,
        "2026-04-13",
        allow_change=False,
    ) == date(2025, 10, 10)
    assert _resolve_course_launch_date(
        existing,
        "2026-04-13",
        allow_change=True,
    ) == date(2026, 4, 13)


def test_historical_scope_requires_explicit_recorded_lesson_confirmation():
    lessons = [lesson(1, status="completed", session_date=date(2026, 4, 13))]

    with pytest.raises(ValueError, match="would move 1 completed or recorded lesson"):
        _select_schedule_change_lessons(
            lessons,
            scope="all",
            effective_date=None,
            launch_date=date(2025, 10, 10),
            today=date(2026, 7, 13),
        )


def test_confirmed_historical_scope_reports_moved_recorded_lessons():
    lessons = [
        lesson(1, status="completed", session_date=date(2026, 4, 13)),
        lesson(2, session_date=date(2026, 4, 15)),
    ]

    selected, anchor, protected_count, moved_count = _select_schedule_change_lessons(
        lessons,
        scope="all",
        effective_date=None,
        launch_date=date(2025, 10, 10),
        allow_recorded_lesson_changes=True,
        today=date(2026, 7, 13),
    )

    assert [row["id"] for row in selected] == [1, 2]
    assert anchor == date(2025, 10, 10)
    assert protected_count == 1
    assert moved_count == 1


def test_first_setup_of_imported_group_preserves_history_and_starts_in_future():
    lessons = [
        lesson(1, status="completed", session_date=date(2026, 4, 13)),
        lesson(2, session_date=date(2026, 4, 15), recorded=True),
        lesson(3),
    ]

    selected, anchor, protected_count, moved_count = _select_schedule_change_lessons(
        lessons,
        scope="",
        effective_date=None,
        launch_date=date(2025, 10, 10),
        today=date(2026, 7, 13),
    )

    assert [row["id"] for row in selected] == [3]
    assert anchor == date(2026, 7, 13)
    assert protected_count == 2
    assert moved_count == 0
