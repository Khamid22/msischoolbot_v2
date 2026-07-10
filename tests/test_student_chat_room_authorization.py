"""Student chat rooms are enrollment-scoped, not prefix-authorized."""

import pytest
from fastapi import HTTPException

import backend.modules.students.chat_api as chat_api
from backend.modules.communication import chat_service
from backend.core.access.dependencies import CurrentUser


class _Result:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


class _Connection:
    def __init__(self, allowed):
        self.allowed = allowed
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, sql, params=None):
        self.calls.append((sql, tuple(params or ())))
        return _Result({"allowed": 1} if self.allowed else None)


def test_room_validator_rejects_empty_scoped_rooms():
    assert chat_service.validate_room("global")
    assert chat_service.validate_room("subject:IGCSE Mathematics A")
    assert chat_service.validate_room("group:7A")
    assert not chat_service.validate_room("subject:")
    assert not chat_service.validate_room("group:   ")
    assert not chat_service.validate_room("anything:7A")


def test_subject_room_access_uses_active_enrollment(monkeypatch):
    conn = _Connection(allowed=True)
    monkeypatch.setattr(chat_service, "connect_chat_db", lambda: conn)

    assert chat_service.student_can_access_room(42, "subject:IGCSE Mathematics A")
    assert conn.calls[0][1] == (42, "IGCSE Mathematics A")
    assert "enrollment_status = 'active'" in conn.calls[0][0]


def test_api_rejects_room_when_student_is_not_enrolled(monkeypatch):
    user = CurrentUser(login="MSI00001", role="student", student_db_id=9001)
    monkeypatch.setattr(chat_service, "student_can_access_room", lambda *_args: False)

    with pytest.raises(HTTPException) as exc_info:
        chat_api._require_room_access(user, "group:7A")

    assert exc_info.value.status_code == 403
