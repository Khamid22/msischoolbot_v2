"""Regression coverage for exam-performance row classification."""

from backend.modules.academics.assessments.filters import is_exam_performance_row


def test_exam_performance_filter_excludes_normal_lesson_topics():
    assert not is_exam_performance_row(
        label="Lesson 3 - HCF and LCM",
        exam_name="Lesson 3 - HCF and LCM",
    )
    assert not is_exam_performance_row(
        label="Practice worksheet",
        exam_name="Practice worksheet",
    )
    assert not is_exam_performance_row(
        label="Cancelled final assessment",
        exam_name="Cancelled final assessment",
    )


def test_exam_performance_filter_includes_exam_test_assessment_rows():
    assert is_exam_performance_row(
        label="Half-term Test 1",
        exam_name="Half-term Test 1",
    )
    assert is_exam_performance_row(label="Mock Paper 2", exam_name="Mock Paper 2")
    assert is_exam_performance_row(
        label="Final assessment",
        exam_name="Final assessment",
    )
    assert is_exam_performance_row(
        item_type="exam",
        label="Lesson 8",
        title="Unit checkpoint",
    )
