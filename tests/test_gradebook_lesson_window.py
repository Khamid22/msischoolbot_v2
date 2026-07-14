from datetime import date, timedelta

from backend.modules.academics.gradebook.window import _gradebook_lesson_window


def lesson(number, day):
    return {
        "id": number,
        "lessonNumber": f"Lesson {number}",
        "date": day.strftime("%d/%m/%Y"),
        "status": "scheduled",
        "sourceKind": "lesson",
        "order": number,
    }


def cancellation(identifier, day):
    return {
        "id": -identifier,
        "lessonNumber": "Cancelled",
        "date": day.strftime("%d/%m/%Y"),
        "status": "cancelled",
        "sourceKind": "cancelled",
        "order": identifier,
    }


def test_cancellations_remain_visible_without_consuming_lesson_pagination():
    start = date(2025, 10, 10)
    lessons = [lesson(index, start + timedelta(days=index - 1)) for index in range(1, 16)]
    items = [*lessons, cancellation(101, start + timedelta(days=3)), cancellation(102, start + timedelta(days=8))]

    page, info = _gradebook_lesson_window(items, limit=12, cursor="o0")

    assert info == {
        "totalLessons": 15,
        "startIndex": 0,
        "endIndex": 12,
        "previousCursor": None,
        "nextCursor": "o3",
        "hasPrevious": False,
        "hasNext": True,
    }
    assert len([item for item in page if item["status"] != "cancelled"]) == 12
    assert len([item for item in page if item["status"] == "cancelled"]) == 2


def test_lesson_cursor_uses_curriculum_position_not_visible_column_position():
    start = date(2025, 10, 10)
    items = [lesson(index, start + timedelta(days=index - 1)) for index in range(1, 21)]
    items.extend([cancellation(101, start + timedelta(days=1)), cancellation(102, start + timedelta(days=2))])

    page, info = _gradebook_lesson_window(items, limit=12, cursor="o4")

    visible_lessons = [item["lessonNumber"] for item in page if item["status"] != "cancelled"]
    assert visible_lessons[0] == "Lesson 5"
    assert visible_lessons[-1] == "Lesson 16"
    assert info["startIndex"] == 4
    assert info["endIndex"] == 16
    assert info["totalLessons"] == 20
