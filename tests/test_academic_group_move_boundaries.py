from contextlib import contextmanager

import pytest

from backend.modules.academics.groups import operations as academic_service


class _Result:
    def __init__(self, row=None):
        self._row = row

    def fetchone(self):
        return self._row


class _Connection:
    def __init__(self, *, target_school_id, target_program_id):
        self.target_school_id = target_school_id
        self.target_program_id = target_program_id
        self.write_attempted = False

    def execute(self, sql, params=()):
        if "FROM msi_v2.group_students gs" in sql:
            return _Result(
                {
                    "group_id": 10,
                    "student_id": 20,
                    "legacy_enrollment_id": 30,
                    "enrollment_status": "active",
                    "legacy_group_id": 40,
                    "v2_group_id": 10,
                    "school_id": 1,
                    "program_id": 2,
                }
            )
        if "FROM msi_v2.groups g" in sql:
            return _Result(
                {
                    "id": 11,
                    "school_id": self.target_school_id,
                    "program_id": self.target_program_id,
                }
            )
        self.write_attempted = True
        return _Result()


@contextmanager
def _connection_context(connection):
    yield connection


@pytest.mark.parametrize(
    ("target_school_id", "target_program_id", "message"),
    [
        (9, 2, "same school"),
        (1, 8, "same subject program"),
    ],
)
def test_move_enrollment_rejects_cross_boundary_target(
    monkeypatch,
    target_school_id,
    target_program_id,
    message,
):
    connection = _Connection(
        target_school_id=target_school_id,
        target_program_id=target_program_id,
    )
    monkeypatch.setattr(
        academic_service,
        "connect_auth_db",
        lambda: _connection_context(connection),
    )

    with pytest.raises(ValueError, match=message):
        academic_service.move_enrollment_group(30, 50)

    assert connection.write_attempted is False
