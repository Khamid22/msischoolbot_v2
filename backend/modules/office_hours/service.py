from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from backend.core.database import connect_auth_db
from backend.modules.office_hours import repository

SCHOOL_TIMEZONE = ZoneInfo("Asia/Tashkent")


def _connect():
    return connect_auth_db()


def _parse_instant(value, field_name):
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name} is required.")
    try:
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a valid date and time.") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=SCHOOL_TIMEZONE)
    return parsed.astimezone(UTC)


def create_availability(
    teacher_id: int,
    subject_id: int,
    starts_at: str,
    ends_at: str,
    slot_minutes: int,
    room: str,
    capacity: int,
    planned_topic: str = "",
) -> int:
    if int(teacher_id or 0) <= 0:
        raise ValueError("Teacher is required.")
    if subject_id is not None and int(subject_id or 0) <= 0:
        raise ValueError("Subject is required.")
    parsed_start = _parse_instant(starts_at, "Start time")
    parsed_end = _parse_instant(ends_at, "End time")
    if parsed_start <= datetime.now(UTC):
        raise ValueError("Office hours must start in the future.")
    if parsed_end <= parsed_start:
        raise ValueError("End time must be after the start time.")
    duration_minutes = int((parsed_end - parsed_start).total_seconds() // 60)
    parsed_slot_minutes = int(slot_minutes or 0)
    if parsed_slot_minutes < 5 or parsed_slot_minutes > 180:
        raise ValueError("Slot length must be between 5 and 180 minutes.")
    if duration_minutes != parsed_slot_minutes:
        raise ValueError("End time must match the selected slot length.")
    parsed_capacity = int(capacity or 0)
    if parsed_capacity < 1 or parsed_capacity > 50:
        raise ValueError("Capacity must be between 1 and 50 students.")

    with _connect() as conn:
        repository.lock_teacher_availability_scope(conn, int(teacher_id))
        if not repository.teacher_has_active_subject(conn, int(teacher_id), subject_id):
            raise ValueError("The selected teacher is not assigned to this subject.")
        if repository.find_teacher_availability_overlap(
            conn,
            int(teacher_id),
            parsed_start.isoformat(),
            parsed_end.isoformat(),
        ):
            raise ValueError("This teacher already has overlapping office hours.")
        return repository.create_availability_row(
            conn,
            teacher_id=teacher_id,
            subject_id=subject_id,
            starts_at=parsed_start.isoformat(),
            ends_at=parsed_end.isoformat(),
            slot_minutes=parsed_slot_minutes,
            room=room,
            capacity=parsed_capacity,
            status='active',
            planned_topic=str(planned_topic or "").strip(),
        )


def list_availabilities(teacher_id=None, subject_id=None, status=None, starts_at_from=None):
    with _connect() as conn:
        rows = repository.list_availabilities_rows(
            conn,
            teacher_id=teacher_id,
            subject_id=subject_id,
            status=status,
            starts_at_from=starts_at_from
        )
        return [dict(row) for row in rows]


def cancel_availability(availability_id: int, *, teacher_id: int | None = None):
    with _connect() as conn:
        availability = repository.get_availability_row(conn, availability_id)
        if not availability:
            raise ValueError("Availability slot was not found.")
        if teacher_id is not None and int(availability["teacher_id"]) != int(teacher_id):
            raise PermissionError("You can only manage your own availability slots.")

        # First cancel availability itself
        repository.update_availability_status_row(conn, availability_id, 'cancelled')
        # Also cancel all active bookings associated with it
        bookings = repository.list_bookings_rows(conn, availability_id=availability_id, status='booked')
        for booking in bookings:
            repository.update_booking_status_row(conn, booking['id'], 'cancelled', teacher_note='Availability was cancelled by teacher.')
        return True


def create_booking(
    availability_id: int,
    student_db_id: int,
    student_note: str = '',
    student_topic_request: str = '',
) -> int:
    with _connect() as conn:
        availability = repository.get_availability_row(conn, availability_id)
        if not availability or availability['status'] not in {'active', 'open'}:
            raise ValueError("This availability slot is no longer active.")
        if _parse_instant(availability["starts_at"], "Start time") <= datetime.now(UTC):
            raise ValueError("Past office hours cannot be booked.")

        active_bookings = repository.list_bookings_rows(conn, availability_id=availability_id, status='booked')
        if len(active_bookings) >= availability['capacity']:
            raise ValueError("This slot has reached its booking capacity.")

        # Check if this student already booked this availability
        already_booked = any(int(b['student_db_id']) == int(student_db_id) for b in active_bookings)
        if already_booked:
            raise ValueError("You have already booked this slot.")

        booking_id = repository.create_booking_row(
            conn,
            availability_id=availability_id,
            teacher_id=int(availability["teacher_id"]),
            student_db_id=student_db_id,
            subject_id=availability["subject_id"],
            starts_at=availability["starts_at"],
            ends_at=availability["ends_at"],
            status='booked',
            student_note=student_note,
            teacher_note='',
            student_topic_request=str(student_topic_request or "").strip(),
        )
        if not booking_id:
            raise ValueError("Student account could not be matched to this booking.")
        return booking_id


def list_bookings(
    availability_id=None,
    teacher_id=None,
    student_db_id=None,
    student_row_id=None,
    subject_id=None,
    status=None,
    starts_at_from=None,
):
    with _connect() as conn:
        rows = repository.list_bookings_rows(
            conn,
            availability_id=availability_id,
            teacher_id=teacher_id,
            student_db_id=student_db_id,
            student_row_id=student_row_id,
            subject_id=subject_id,
            status=status,
            starts_at_from=starts_at_from
        )
        return [dict(row) for row in rows]


def update_booking_status(
    booking_id: int,
    status: str,
    teacher_note: str = None,
    *,
    teacher_id: int | None = None,
    student_db_id: int | None = None,
):
    valid_statuses = {'booked', 'cancelled', 'completed', 'no_show'}
    if status not in valid_statuses:
        raise ValueError(f"Invalid status. Must be one of {valid_statuses}")
    with _connect() as conn:
        booking = repository.get_booking_row(conn, booking_id)
        if not booking:
            raise ValueError("Booking was not found.")
        if teacher_id is not None and int(booking["teacher_id"]) != int(teacher_id):
            raise PermissionError("You can only manage bookings for your own office hours.")
        if student_db_id is not None and int(booking["student_db_id"]) != int(student_db_id):
            raise PermissionError("You can only manage your own bookings.")
        return repository.update_booking_status_row(conn, booking_id, status, teacher_note)
