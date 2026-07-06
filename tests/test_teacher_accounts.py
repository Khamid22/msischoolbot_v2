from backend.identity.teachers import subject_teacher_login_prefix


def test_subject_teacher_login_prefix_examples():
    assert subject_teacher_login_prefix("IGCSE Mathematics A") == "math"
    assert subject_teacher_login_prefix("English as a Second Language") == "eng"
    assert subject_teacher_login_prefix("Biology") == "bio"


def test_teacher_workspace_includes_academy_payload(monkeypatch):
    from backend.roles.teacher import services

    monkeypatch.setattr(
        services,
        "get_teacher_by_id",
        lambda teacher_id: {
            "id": teacher_id,
            "full_name": "Omnia",
            "login": "engt001",
            "assigned_group": "",
            "category": "junior",
            "semester_stage": "1-2",
            "performance_score": 7,
        },
    )
    monkeypatch.setattr(
        services,
        "get_academy_teacher_for_teacher_account",
        lambda teacher_id, staff_id=None: {
            "id": 3,
            "user_id": staff_id,
            "account_teacher_id": teacher_id,
            "promoted_teacher_id": 0,
            "assignments": [
                {"id": 8, "session_datetime": "2026-05-01T08:00:00Z"},
                {"id": 9, "session_datetime": ""},
            ],
            "assessments": [{"id": 11, "lesson_assignment_id": 8}],
        },
    )

    workspace = services.build_teacher_workspace(12, staff_id=44)

    assert workspace["teacher"]["login"] == "engt001"
    assert workspace["academy"]["id"] == 3
    assert [row["id"] for row in workspace["journey"]] == [8, 9]
    assert [row["id"] for row in workspace["lesson_reports"]] == [11]
    assert [row["id"] for row in workspace["training_timetable"]] == [8]
