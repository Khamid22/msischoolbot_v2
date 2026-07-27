from datetime import UTC, datetime, timedelta

import pytest

from backend.modules.domains.academics.timetable import office_hours_service as service
from backend.modules.domains.academics.timetable import office_hours_repository as repository


def test_naive_office_hour_times_are_interpreted_in_tashkent():
    parsed = service._parse_instant("2030-01-02T10:00", "Start time")

    assert parsed.isoformat() == "2030-01-02T05:00:00+00:00"


def test_create_availability_rejects_inconsistent_slot_duration():
    start = datetime.now(UTC) + timedelta(days=1)
    end = start + timedelta(minutes=20)

    with pytest.raises(ValueError, match="slot length"):
        service.create_availability(
            teacher_id=1,
            subject_id=2,
            starts_at=start.isoformat(),
            ends_at=end.isoformat(),
            slot_minutes=30,
            room="Room 1",
            capacity=1,
        )


def test_create_availability_rejects_past_slots_before_database_access(monkeypatch):
    monkeypatch.setattr(
        service,
        "_connect",
        lambda: (_ for _ in ()).throw(AssertionError("database must not be opened")),
    )
    start = datetime.now(UTC) - timedelta(hours=2)
    end = start + timedelta(minutes=30)

    with pytest.raises(ValueError, match="future"):
        service.create_availability(
            teacher_id=1,
            subject_id=2,
            starts_at=start.isoformat(),
            ends_at=end.isoformat(),
            slot_minutes=30,
            room="Room 1",
            capacity=1,
        )


def test_booking_queries_authorize_with_canonical_student_id():
    class Result:
        def fetchone(self):
            return {"id": 14}

    class Connection:
        def __init__(self):
            self.sql = ""
            self.params = ()

        def execute(self, sql, params=()):
            self.sql = sql
            self.params = params
            return Result()

    conn = Connection()
    booking_id = repository.create_booking_row(
        conn,
        availability_id=3,
        teacher_id=2,
        student_db_id=71,
        subject_id=4,
        starts_at="2030-01-01T05:00:00+00:00",
        ends_at="2030-01-01T05:30:00+00:00",
    )

    assert booking_id == 14
    assert "WHERE st.id = %s" in conn.sql
    assert "legacy_student_row_id = %s" not in conn.sql
    assert conn.params[-1] == 71
