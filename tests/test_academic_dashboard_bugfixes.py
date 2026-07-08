"""Regression tests for scoped Academic Dashboard UI bug fixes."""

from pathlib import Path

from backend.domains.academics.exam_filters import is_exam_performance_row
from backend.roles.admin.services.insights_service import build_admin_subject_counts, build_admin_subject_info


def test_audit_settings_placeholder_card_is_not_rendered():
    admin_source = Path("frontend/src/roles/admin/pages/Admin.tsx").read_text()

    assert "Audit / Settings" not in admin_source
    assert "xl:grid-cols-4" in admin_source
    assert "xl:grid-cols-5" not in admin_source
    # The account-identity cards were replaced by overview stat cards with
    # hover breakdowns computed from the quick stats already on the page.
    assert "Total Accounts" not in admin_source
    assert "overviewStatCards" in admin_source
    assert "group-hover:opacity-100" in admin_source
    assert "bg-surface/85" in admin_source


def test_subject_hover_counts_distinct_database_students_per_subject():
    metrics = [
        {
            "school_key": "school5",
            "school_name": "School 5",
            "student_key": "101",
            "full_name": "Example Learner",
            "subject": "IGCSE Mathematics A",
            "group": "7A",
        },
        {
            "school_key": "sehriyo",
            "school_name": "Sehriyo",
            "student_key": "101",
            "full_name": "Example Learner",
            "subject": "IGCSE Mathematics A",
            "group": "7B",
        },
        {
            "school_key": "school5",
            "school_name": "School 5",
            "student_key": "102",
            "full_name": "Second Learner",
            "subject": "English as a Second Language",
            "group": "8A",
        },
    ]

    assert build_admin_subject_counts(metrics) == [
        {"subject_name": "IGCSE Mathematics A", "count": 1},
        {"subject_name": "English as a Second Language", "count": 1},
    ]


def test_exam_performance_filter_excludes_normal_lesson_topics():
    assert not is_exam_performance_row(label="Lesson 3 - HCF and LCM", exam_name="Lesson 3 - HCF and LCM")
    assert not is_exam_performance_row(label="Practice worksheet", exam_name="Practice worksheet")
    assert not is_exam_performance_row(label="Cancelled final assessment", exam_name="Cancelled final assessment")


def test_exam_performance_filter_includes_only_exam_test_assessment_rows():
    assert is_exam_performance_row(label="Half-term Test 1", exam_name="Half-term Test 1")
    assert is_exam_performance_row(label="Mock Paper 2", exam_name="Mock Paper 2")
    assert is_exam_performance_row(label="Final assessment", exam_name="Final assessment")
    assert is_exam_performance_row(item_type="exam", label="Lesson 8", title="Unit checkpoint")


def test_subject_performance_exam_series_ignores_lesson_like_exam_rows():
    metrics = [
        {
            "school_key": "school5",
            "school_name": "School 5",
            "full_name": "Example Learner",
            "subject": "Mathematics",
            "group": "7A",
            "aap": 7.0,
            "ar": 90,
        }
    ]
    dataset = {
        "dashboards_by_id": {
            1: {
                "student": {
                    "schoolCode": "school5",
                    "schoolName": "School 5",
                    "subject": "Mathematics",
                    "group": "7A",
                },
                "homeworkGrades": [],
                "attendanceLessons": [],
                "examResults": [
                    {"label": "Lesson 3 - HCF and LCM", "examName": "Lesson 3 - HCF and LCM", "score": 9},
                    {"label": "Half-term Test 1", "examName": "Half-term Test 1", "score": 7},
                    {"label": "Final assessment", "examName": "Final assessment", "score": 8},
                ],
            }
        }
    }

    subject_rows = build_admin_subject_info(metrics, dataset=dataset)

    assert len(subject_rows) == 1
    assert subject_rows[0]["exam_labels"] == ["HFT1", "Final assessment"]
    assert subject_rows[0]["exam_series"] == [{"label": "7A", "values": [7.0, 8.0]}]


def test_performance_graph_uses_responsive_full_width_layout():
    source = Path("frontend/src/roles/admin/panels/overview/SchoolOverviewPanel.tsx").read_text()

    assert "graphLineSeries.length * 70" not in source
    # The chart fills the available vertical space instead of forcing tall
    # fixed heights that clip the x-axis labels and legend.
    assert 'className="h-full min-h-[19rem] min-w-full"' in source
    assert "sm:h-[32rem]" not in source
    assert "lg:h-[35rem]" not in source
    assert '<ResponsiveContainer width="100%" height="100%">' in source
    assert "No exam performance data yet." in source
    # Month points stay chronological; only the legend order is ranked.
    assert "sortedAcademicClassLineData" not in source
    assert 'graphMetric === "exam" ? examClassLineData : academicClassLineData' in source
