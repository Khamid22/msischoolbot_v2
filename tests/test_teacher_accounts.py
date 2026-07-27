from backend.modules.domains.teacher_records.service import subject_teacher_login_prefix


def test_subject_teacher_login_prefix_examples():
    assert subject_teacher_login_prefix("IGCSE Mathematics A") == "math"
    assert subject_teacher_login_prefix("English as a Second Language") == "eng"
    assert subject_teacher_login_prefix("Biology") == "bio"


def test_teacher_portal_workspace_services_are_removed():
    from pathlib import Path

    assert not Path("backend/modules/staff_records/teachers_workspace.py").exists()
    assert not Path("backend/modules/staff_records/teachers_cards.py").exists()
