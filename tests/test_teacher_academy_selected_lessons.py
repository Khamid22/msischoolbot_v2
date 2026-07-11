"""Teacher Academy selected curriculum lesson creation coverage."""

from pathlib import Path

import backend.modules.staff_records.development_service as academy_service


class _Rows:
    def __init__(self, rows):
        self._rows = rows

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return self._rows


class _AcademyCreateConnection:
    def __init__(self, curriculum_rows):
        self.curriculum_rows = curriculum_rows
        self.assignments = []
        self.notifications = []
        self.commits = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def execute(self, sql, params=None):
        if "FROM msi_v2.subject_programs" in sql:
            return _Rows(
                [
                    {
                        "id": 7,
                        "subject_id": 2,
                        "program_name": "IGCSE Mathematics",
                        "subject_name": "Mathematics",
                        "subject_key": "math",
                    }
                ]
            )
        if "FROM msi_v2.subject_program_items" in sql:
            program_id = int(params[0])
            return _Rows(
                [
                    row
                    for row in self.curriculum_rows
                    if int(row["program_id"]) == program_id and row["item_type"] == "lesson"
                ]
            )
        if "INSERT INTO msi_v2.academy_teachers" in sql:
            return _Rows([{"id": 91}])
        if "INSERT INTO msi_v2.academy_lesson_assignments" in sql:
            self.assignments.append(params)
            return _Rows([])
        return _Rows([])

    def commit(self):
        self.commits += 1


def _curriculum_rows():
    return [
        {
            "id": 101,
            "program_id": 7,
            "item_order": 1,
            "item_type": "lesson",
            "lesson_number": "L1",
            "title": "Numbers",
            "specification_points": "1.1",
            "book_pages": "10-11",
        },
        {
            "id": 102,
            "program_id": 7,
            "item_order": 2,
            "item_type": "exam",
            "lesson_number": "E1",
            "title": "Checkpoint",
            "specification_points": "",
            "book_pages": "",
        },
        {
            "id": 103,
            "program_id": 7,
            "item_order": 3,
            "item_type": "lesson",
            "lesson_number": "L3",
            "title": "Algebra",
            "specification_points": "2.1",
            "book_pages": "20-21",
        },
        {
            "id": 201,
            "program_id": 8,
            "item_order": 1,
            "item_type": "lesson",
            "lesson_number": "X1",
            "title": "Other Program Lesson",
            "specification_points": "",
            "book_pages": "",
        },
    ]


def _patch_create_dependencies(monkeypatch, curriculum_rows=None):
    conn = _AcademyCreateConnection(curriculum_rows or _curriculum_rows())
    monkeypatch.setattr(academy_service.repository, "connect_auth_db", lambda: conn)
    monkeypatch.setattr(academy_service.repository, "insert_teacher_profile_row", lambda *args, **kwargs: 44)
    monkeypatch.setattr(academy_service.repository, "get_next_teacher_code", lambda conn: "TCH0004")
    monkeypatch.setattr(academy_service.repository, "insert_teacher_auth", lambda *args, **kwargs: 55)
    monkeypatch.setattr(academy_service, "_provision_teacher_account_v2", lambda *args, **kwargs: 0)
    monkeypatch.setattr(
        academy_service,
        "_notify_academy_event_safe",
        lambda **kwargs: conn.notifications.append(kwargs)
        or {"ok": True, "telegram_sent": False, "in_app_available": True},
    )
    return conn


def test_create_academy_teacher_uses_selected_lesson_ids_in_order(monkeypatch):
    conn = _patch_create_dependencies(monkeypatch)
    assert not hasattr(academy_service, "_balanced_random_lessons")

    created, message, credentials = academy_service.create_academy_teacher(
        full_name="Example Teacher",
        subject_program_id=7,
        selected_curriculum_item_ids=[103, 101],
        created_by="Academic Director",
        return_credentials=True,
    )

    assert created is True
    assert message == ""
    assert credentials["teacher_code"] == "TCH0004"
    assert [params[3] for params in conn.assignments] == [103, 101]
    assert [params[4] for params in conn.assignments] == [1, 2]
    assert [params[6] for params in conn.assignments] == ["Algebra", "Numbers"]
    assert conn.notifications[0]["event_type"] == "teacher_created"
    assert conn.notifications[0]["title"] == "Welcome to MSI School"
    assert conn.notifications[0]["academy_teacher"]["full_name"] == "Example Teacher"
    assert conn.notifications[0]["academy_teacher"]["subject"] == "Mathematics"
    assert "lessons" not in conn.notifications[0]["body"]
    assert conn.commits == 1


def test_create_academy_teacher_rejects_zero_selected_lessons(monkeypatch):
    conn = _patch_create_dependencies(monkeypatch)

    created, message, _credentials = academy_service.create_academy_teacher(
        full_name="Example Teacher",
        subject_program_id=7,
        selected_curriculum_item_ids=[],
        return_credentials=True,
    )

    assert created is False
    assert message == "Select at least 1 Teacher Academy lesson."
    assert conn.assignments == []
    assert conn.commits == 0


def test_create_academy_teacher_rejects_invalid_lesson_id(monkeypatch):
    conn = _patch_create_dependencies(monkeypatch)

    created, message, _credentials = academy_service.create_academy_teacher(
        full_name="Example Teacher",
        subject_program_id=7,
        selected_curriculum_item_ids=["not-a-lesson"],
        return_credentials=True,
    )

    assert created is False
    assert message == "Select valid Teacher Academy lessons."
    assert conn.assignments == []


def test_create_academy_teacher_rejects_cross_program_or_non_lesson_ids(monkeypatch):
    conn = _patch_create_dependencies(monkeypatch)

    created, message, _credentials = academy_service.create_academy_teacher(
        full_name="Example Teacher",
        subject_program_id=7,
        selected_curriculum_item_ids=[201],
        return_credentials=True,
    )

    assert created is False
    assert message == "Selected Teacher Academy lessons must be lesson items from the selected subject curriculum."
    assert conn.assignments == []

    created, message, _credentials = academy_service.create_academy_teacher(
        full_name="Example Teacher",
        subject_program_id=7,
        selected_curriculum_item_ids=[102],
        return_credentials=True,
    )

    assert created is False
    assert message == "Selected Teacher Academy lessons must be lesson items from the selected subject curriculum."
    assert conn.assignments == []


def test_teacher_academy_frontend_source_includes_selected_lesson_ui():
    source = Path("frontend/src/features/management/teachers/TeacherAcademyPanel.tsx").read_text()

    assert "Select Academy Lessons" in source
    assert "Selected {selectedLessonIds.length} lessons" in source
    assert 'name="academy_curriculum_item_ids"' in source
    assert 'type="checkbox"' in source
    assert "Select first 6" in source
    assert "Select first 12" in source
    assert "Select visible" in source
    assert "Clear selection" in source
    assert "Show details" in source
    assert "Review & Create" in source
    assert "Select at least 1 Teacher Academy lesson." in source
