"""Domain-service behavior for syncing selected Teacher Academy lessons."""

from contextlib import contextmanager

import pytest


class _FakeConn:
    def __init__(self):
        self.committed = False

    def commit(self):
        self.committed = True


@pytest.fixture
def sync_env(monkeypatch):
    from backend.modules.domains.teacher_academy import service as service
    from backend.modules.domains.teacher_academy import repository as repository
    from backend.modules.domains.teacher_academy import mutations_repository

    conn = _FakeConn()
    calls = {
        "deleted": [],
        "sequenced": [],
        "inserted": [],
        "touched": [],
        "notified": [],
    }

    @contextmanager
    def fake_connect():
        yield conn

    monkeypatch.setattr(service, "connect_auth_db", fake_connect)
    monkeypatch.setattr(
        mutations_repository,
        "get_academy_teacher_program_row",
        lambda _conn, teacher_id: {
            "id": teacher_id,
            "full_name": "Example Teacher",
            "subject_id": 2,
            "subject": "Mathematics",
            "subject_program_id": 7,
            "telegram_username": "example_teacher",
            "telegram_user_id": 901234,
        },
    )
    monkeypatch.setattr(
        repository,
        "get_subject_program",
        lambda _conn, program_id: {"id": program_id, "subject_id": 2, "subject_name": "Mathematics"},
    )
    monkeypatch.setattr(
        repository,
        "list_curriculum_lessons",
        lambda _conn, _program_id: [
            {"id": 101, "lesson_number": "Lesson 1", "title": "Fractions"},
            {"id": 102, "lesson_number": "Lesson 2", "title": "Decimals"},
            {"id": 103, "lesson_number": "Lesson 3", "title": "HCF and LCM"},
        ],
    )
    monkeypatch.setattr(
        repository,
        "list_assignment_rows",
        lambda _conn, _teacher_id: [
            {"id": 501, "curriculum_item_id": 101},
            {"id": 502, "curriculum_item_id": 102},
        ],
    )
    monkeypatch.setattr(
        mutations_repository,
        "delete_assignment_rows_with_assessments",
        lambda _conn, assignment_ids: calls["deleted"].extend(assignment_ids),
    )
    monkeypatch.setattr(
        mutations_repository,
        "update_assignment_sequence",
        lambda _conn, **kwargs: calls["sequenced"].append(kwargs),
    )
    monkeypatch.setattr(
        mutations_repository,
        "insert_academy_lesson_assignment",
        lambda _conn, **kwargs: calls["inserted"].append(kwargs),
    )
    monkeypatch.setattr(
        mutations_repository,
        "touch_academy_teacher",
        lambda _conn, **kwargs: calls["touched"].append(kwargs),
    )
    monkeypatch.setattr(
        service,
        "_notify_academy_event_safe",
        lambda **kwargs: calls["notified"].append(kwargs),
    )
    return service, conn, calls


def test_sync_adds_new_lessons_removes_unticked_and_resequences(sync_env):
    service, conn, calls = sync_env

    ok, error = service.sync_academy_lessons(
        academy_teacher_id=91,
        selected_curriculum_item_ids="102,103",
        created_by="HOD0001",
    )

    assert (ok, error) == (True, "")
    # Item 101 was unticked, so its assignment (and reports) go away.
    assert calls["deleted"] == [501]
    # The kept assignment is resequenced to the new order.
    assert calls["sequenced"][0]["assignment_id"] == 502
    assert calls["sequenced"][0]["sequence_no"] == 1
    # Item 103 is newly ticked and inserted at position 2.
    assert len(calls["inserted"]) == 1
    inserted = calls["inserted"][0]
    assert inserted["curriculum_item_id"] == 103
    assert inserted["sequence_no"] == 2
    assert inserted["lesson_topic"] == "HCF and LCM"
    assert inserted["created_by"] == "HOD0001"
    assert conn.committed
    assert calls["notified"]
    notification = calls["notified"][0]
    assert notification["academy_teacher"]["full_name"] == "Example Teacher"
    assert notification["academy_teacher"]["telegram_user_id"] == 901234
    assert notification["lessons_count"] == 2


def test_sync_rejects_empty_selection_and_foreign_curriculum_items(sync_env):
    service, _conn, calls = sync_env

    ok, error = service.sync_academy_lessons(
        academy_teacher_id=91,
        selected_curriculum_item_ids="",
    )
    assert ok is False
    assert "at least 1" in error

    ok, error = service.sync_academy_lessons(
        academy_teacher_id=91,
        selected_curriculum_item_ids="102,999",
    )
    assert ok is False
    assert "lesson items from the selected subject curriculum" in error
    assert calls["deleted"] == []
    assert calls["inserted"] == []
