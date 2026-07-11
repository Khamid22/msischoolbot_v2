from backend.modules.student_records.dashboard import extract_program_total_lessons
from backend.modules.parent_access.service import _average_program_completion


def test_program_total_comes_from_canonical_payload():
    payload = {"student": {"programLessonCount": 112}}

    assert extract_program_total_lessons(payload, {}, "IGCSE Biology", "8A") == 112


def test_program_total_falls_back_to_unique_catalog_lessons_without_inventing_180():
    dataset = {
        "lesson_catalog_by_subject_group": {
            "Mathematics": {
                "8A": [
                    {"lesson_number": "L1"},
                    {"lesson_number": "L2"},
                    {"lesson_number": "L2"},
                ]
            }
        }
    }

    assert extract_program_total_lessons({}, dataset, "Mathematics", "8A") == 2
    assert extract_program_total_lessons({}, {}, "Mathematics", "8A") == 0


def test_parent_program_progress_is_weighted_by_real_subject_lengths():
    progress = _average_program_completion(
        [
            {"program_completed_lessons": 56, "program_total_lessons": 112},
            {"program_completed_lessons": 86, "program_total_lessons": 172},
        ]
    )

    assert progress == {
        "program_completion_rate": 50,
        "program_completed_lessons": 142,
        "program_total_lessons": 284,
    }
