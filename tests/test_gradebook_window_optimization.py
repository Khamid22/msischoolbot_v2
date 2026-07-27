import ast
from datetime import date, datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _window_function():
    operations = (ROOT / "backend/modules/domains/academics/gradebook/window.py").read_text(encoding="utf-8")
    tree = ast.parse(operations)
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_gradebook_lesson_window"
    )

    class Canonical:
        @staticmethod
        def parse_date(value):
            if isinstance(value, date):
                return value
            for date_format in ("%d/%m/%Y", "%Y-%m-%d"):
                try:
                    return datetime.strptime(str(value), date_format).date()
                except ValueError:
                    continue
            return None

    namespace = {"canonical": Canonical, "date": date}
    exec(compile(ast.Module(body=[function], type_ignores=[]), "<gradebook-window>", "exec"), namespace)
    return namespace["_gradebook_lesson_window"]


def _lessons(count=30):
    start = date(2026, 1, 1)
    return [
        {
            "id": index + 1,
            "lessonNumber": f"Lesson {index + 1}",
            "date": (start + timedelta(days=index)).strftime("%d/%m/%Y"),
        }
        for index in range(count)
    ]


def test_gradebook_window_limits_rendered_lessons_and_exposes_navigation():
    page, info = _window_function()(
        _lessons(), limit=12, anchor_date="10/01/2026"
    )

    assert len(page) == 12
    assert info["totalLessons"] == 30
    assert info["hasNext"] is True
    assert info["nextCursor"]


def test_gradebook_cursor_returns_stable_next_window():
    window = _window_function()
    first, first_info = window(_lessons(), limit=12, cursor="o0")
    second, second_info = window(
        _lessons(), limit=12, cursor=first_info["nextCursor"]
    )

    assert first[-1]["id"] == 12
    assert second[0]["id"] == 13
    assert second_info["hasPrevious"] is True


def test_gradebook_month_returns_only_that_calendar_month():
    page, info = _window_function()(_lessons(70), month="2026-02")

    assert page[0]["date"] == "01/02/2026"
    assert page[-1]["date"] == "28/02/2026"
    assert len(page) == 28
    assert info["selectedMonth"] == "2026-02"
    assert info["previousMonth"] == "2026-01"
    assert info["nextMonth"] == "2026-03"
    assert [option["label"] for option in info["monthOptions"]] == [
        "January 2026",
        "February 2026",
        "March 2026",
    ]


def test_gradebook_empty_requested_month_stays_selected():
    page, info = _window_function()(_lessons(40), month="2026-04")

    assert page == []
    assert info["selectedMonth"] == "2026-04"
    assert info["previousMonth"] == "2026-02"
    assert info["nextMonth"] is None
    assert info["monthOptions"][-1] == {
        "value": "2026-04",
        "label": "April 2026",
        "lessonCount": 0,
    }


def test_gradebook_empty_month_without_any_dated_lessons_is_selectable():
    page, info = _window_function()(
        [{"id": 1, "lessonNumber": "Lesson 1", "date": ""}],
        month="2026-04",
    )

    assert page == []
    assert info["selectedMonth"] == "2026-04"
    assert info["monthOptions"] == [
        {"value": "2026-04", "label": "April 2026", "lessonCount": 0}
    ]


def test_gradebook_month_keeps_cancellations_in_their_calendar_month():
    items = _lessons(40)
    items.append({
        "id": -1,
        "lessonNumber": "Cancelled",
        "date": "15/01/2026",
        "status": "cancelled",
        "sourceKind": "cancellation",
        "isCancellation": True,
    })

    page, info = _window_function()(items, month="2026-01")

    assert any(item.get("isCancellation") for item in page)
    assert info["monthOptions"][0]["lessonCount"] == 31


def test_gradebook_get_is_read_only_and_records_are_id_keyed():
    gradebook_source = (ROOT / "backend/modules/domains/academics/gradebook/service.py").read_text(
        encoding="utf-8"
    )

    assert "INSERT INTO msi_v2.lesson_sessions" not in gradebook_source
    assert "conn.commit()" not in gradebook_source
    assert '"attendanceByLessonId"' in gradebook_source
    assert '"homeworkByLessonId"' in gradebook_source


def test_gradebook_performance_migration_is_non_destructive():
    migration = (ROOT / "database/alembic/versions/0011_gradebook_performance.py").read_text(
        encoding="utf-8"
    )

    assert "idx_attendance_gradebook_lookup" in migration
    assert "idx_homework_gradebook_lookup" in migration
    assert "idx_exam_gradebook_lookup" in migration
    assert "DELETE FROM" not in migration
    assert "TRUNCATE" not in migration


def test_frontend_uses_month_navigation_and_stable_lesson_ids():
    source = (ROOT / "frontend/src/features/academics/gradebook/GroupGradebook.tsx").read_text(
        encoding="utf-8"
    )

    assert "Previous month" in source
    assert "Next month" in source
    assert 'type GradebookDisplayMode = "table" | "chart"' in source
    assert 'aria-pressed={selected}' in source
    assert "PeriodFilter" not in source
    assert "Lessons {data.pageInfo.startIndex" not in source
    assert ">Loading…</div>" not in source
    assert "attendanceByLessonId" in source
    assert "homeworkByLessonId" in source
    assert "unscheduledLessonCount" in source


def test_gradebook_charts_are_compact_animated_and_motion_safe():
    source = (ROOT / "frontend/src/features/academics/gradebook/GroupGradebook.tsx").read_text(
        encoding="utf-8"
    )

    assert "min-h-[500px]" not in source
    assert "h-[clamp(19rem,46dvh,32rem)]" in source
    assert 'key={`exam-chart-${selectedExamTypeValue}`}' in source
    assert "isAnimationActive={!prefersReducedMotion}" in source
    assert 'matchMedia("(prefers-reduced-motion: reduce)")' in source
