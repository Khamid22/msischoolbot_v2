import json
from datetime import date
from pathlib import Path

import pytest
from fastapi import HTTPException

from backend.modules.domains.academics.gradebook import trends as operations
from backend.modules.people.academic_director.workspace import academics_api as director_academics_api


ROOT = Path(__file__).resolve().parents[1]


class _Result:
    def __init__(self, rows):
        self.rows = rows

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows


class _TrendConnection:
    def __init__(self, *, group_exists=True):
        self.group_exists = group_exists
        self.aggregation_sql = ""
        self.aggregation_params = ()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def execute(self, sql, params):
        if "FROM msi_v2.academic_calendar_closures" in sql:
            return _Result([])
        if "WITH calendar_months" not in sql:
            return _Result([{"id": 41, "school_id": 5}] if self.group_exists else [])
        self.aggregation_sql = sql
        self.aggregation_params = params
        return _Result(
            [
                {
                    "month_start": date(2025, 11, 1),
                    "avg_aap": None,
                    "avg_ar": None,
                    "avg_performance": None,
                    "lesson_count": 0,
                    "students_with_data": 0,
                    "homework_record_count": 0,
                    "attendance_record_count": 0,
                },
                {
                    "month_start": date(2025, 12, 1),
                    "avg_aap": 6.2,
                    "avg_ar": 80.8,
                    "avg_performance": 6.8,
                    "lesson_count": 12,
                    "students_with_data": 6,
                    "homework_record_count": 67,
                    "attendance_record_count": 70,
                },
            ]
        )


def test_trend_range_includes_selected_month_and_crosses_year_boundary():
    start, through, end, count = operations._gradebook_trend_month_range("2026-04", 6)

    assert start == date(2025, 11, 1)
    assert through == date(2026, 4, 1)
    assert end == date(2026, 5, 1)
    assert count == 6


@pytest.mark.parametrize(
    ("through", "months", "message"),
    [
        ("2026/04", 6, "YYYY-MM"),
        ("2026-13", 6, "valid calendar month"),
        ("2026-04", 2, "between 3 and 12"),
        ("2026-04", 13, "between 3 and 12"),
        ("2026-04", "many", "whole number"),
    ],
)
def test_trend_range_rejects_invalid_queries(through, months, message):
    with pytest.raises(ValueError, match=message):
        operations._gradebook_trend_month_range(through, months)


def test_trend_payload_keeps_empty_months_and_compact_coverage(monkeypatch):
    connection = _TrendConnection()
    monkeypatch.setattr(operations, "connect_auth_db", lambda: connection)

    payload = operations.get_group_gradebook_trends(12, through="2026-04", months=6)

    assert payload["range"] == {"from": "2025-11", "through": "2026-04", "months": 6}
    assert payload["items"][0] == {
        "month": "2025-11",
        "label": "Nov 2025",
        "avgAAP": None,
        "avgAR": None,
        "avgPerformance": None,
        "lessonCount": 0,
        "studentsWithData": 0,
        "homeworkRecordCount": 0,
        "attendanceRecordCount": 0,
        "hasClosure": False,
        "closureTitles": [],
    }
    assert payload["items"][1]["avgAAP"] == 6.2
    assert payload["items"][1]["avgAR"] == 80.8
    assert payload["items"][1]["avgPerformance"] == 6.8
    assert connection.aggregation_params[0] == date(2025, 11, 1)
    assert connection.aggregation_params[1] == date(2026, 4, 1)
    assert "generate_series" in connection.aggregation_sql
    assert "enrollment_status = 'active'" in connection.aggregation_sql
    assert "FULL OUTER JOIN attendance_by_student" in connection.aggregation_sql
    assert "academic_calendar_closures" in connection.aggregation_sql


def test_trend_query_returns_none_for_a_missing_group(monkeypatch):
    monkeypatch.setattr(
        operations,
        "connect_auth_db",
        lambda: _TrendConnection(group_exists=False),
    )

    assert operations.get_group_gradebook_trends(99, through="2026-04") is None


def test_academic_director_handler_returns_success_and_meaningful_errors(monkeypatch):
    api_module = director_academics_api
    payload = {"range": {"from": "2025-11", "through": "2026-04", "months": 6}, "items": []}
    monkeypatch.setattr(api_module, "get_group_gradebook_trends", lambda *args, **kwargs: payload)
    response = api_module.gradebook_trends(12, "2026-04", 6)
    assert json.loads(response.body)["data"] == payload

    monkeypatch.setattr(api_module, "get_group_gradebook_trends", lambda *args, **kwargs: None)
    with pytest.raises(HTTPException) as missing:
        api_module.gradebook_trends(12, "2026-04", 6)
    assert missing.value.status_code == 404

    def invalid(*args, **kwargs):
        raise ValueError("through must use YYYY-MM format.")

    monkeypatch.setattr(api_module, "get_group_gradebook_trends", invalid)
    with pytest.raises(HTTPException) as bad_request:
        api_module.gradebook_trends(12, "bad-month", 6)
    assert bad_request.value.status_code == 400
    assert "YYYY-MM" in bad_request.value.detail


def test_trend_aggregation_is_read_only_and_academic_director_exposes_it():
    trend_source = (ROOT / "backend/modules/domains/academics/gradebook/trends.py").read_text(
        encoding="utf-8"
    )
    assert "INSERT " not in trend_source
    assert "UPDATE " not in trend_source
    assert "DELETE " not in trend_source
    assert "conn.commit()" not in trend_source

    route_source = (
        ROOT / "backend/modules/people/academic_director/workspace/academics_api.py"
    ).read_text(encoding="utf-8")
    assert '"/groups/{group_id}/gradebook-trends"' in route_source
    assert "get_group_gradebook_trends" in route_source


def test_frontend_trends_are_lazy_accessible_and_mutation_aware():
    gradebook = (ROOT / "frontend/src/features/academics/gradebook/GroupGradebook.tsx").read_text(
        encoding="utf-8"
    )
    timetable = (ROOT / "frontend/src/features/academics/timetable/ModernGroupTimetable.tsx").read_text(
        encoding="utf-8"
    )

    assert 'enabled: Boolean(data && activeView === "gradebook" && gradebookDisplay === "chart"' in gradebook
    assert '["academic", "gradebook-trends", groupId, selectedLessonMonth, 6]' in gradebook
    assert '(["trends", "students"] as const)' in gradebook
    assert "connectNulls={false}" in gradebook
    assert '<table className="sr-only">' in gradebook
    assert "isAnimationActive={!prefersReducedMotion}" in gradebook
    assert '["academic", "gradebook-trends", groupId]' in timetable
