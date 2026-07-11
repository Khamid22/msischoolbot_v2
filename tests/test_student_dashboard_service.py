from urllib.parse import parse_qs, urlparse

from backend.modules.student_records import service as student_service
from backend.modules.student_records import dashboard as dashboard_service


def test_subject_switch_options_mark_current_subject_and_group(monkeypatch):
    monkeypatch.setattr(
        student_service,
        "get_student_subject_enrollments",
        lambda _student_id: [
            {
                "student_id": 42,
                "subject": "IGCSE Mathematics A",
                "group": "MG1",
            },
            {
                "student_id": 42,
                "subject": "English as a Second Language",
                "group": "EG1",
            },
        ],
    )

    options = dashboard_service.build_subject_switch_options(
        dataset={},
        current_full_name="Kamoliddin Zokirjonov",
        current_student_id=42,
        current_subject_name="English as a Second Language",
        current_group_name="EG1",
        current_school_code="sehriyo",
    )

    current_options = [option for option in options if option["is_current"]]

    assert len(options) == 2
    assert len(current_options) == 1
    assert current_options[0]["subject"] == "English as a Second Language"

    query = parse_qs(urlparse(current_options[0]["url"]).query)
    assert query["subject"] == ["English as a Second Language"]
    assert query["group"] == ["EG1"]
    assert query["school"] == ["sehriyo"]
