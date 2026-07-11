import ast
from datetime import date, datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _window_function():
    operations = (ROOT / "backend/modules/academics/operations.py").read_text(encoding="utf-8")
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


def test_gradebook_get_is_read_only_and_records_are_id_keyed():
    operations = (ROOT / "backend/modules/academics/operations.py").read_text(encoding="utf-8")
    gradebook_source = operations.split("def get_group_gradebook(", 1)[1].split(
        "def update_enrollment_status(", 1
    )[0]

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


def test_frontend_uses_window_navigation_and_stable_lesson_ids():
    source = (ROOT / "frontend/src/features/management/academic/GroupGradebook.tsx").read_text(
        encoding="utf-8"
    )

    assert "GRADEBOOK_LESSON_WINDOW = 12" in source
    assert "Previous lessons" in source
    assert "Next lessons" in source
    assert "Jump to lesson number" in source
    assert "attendanceByLessonId" in source
    assert "homeworkByLessonId" in source
