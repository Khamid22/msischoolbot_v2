from datetime import datetime
from shared.db import queries


def _connect():
    return queries.connect_auth_db()


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
    with _connect() as conn:
        return queries.create_availability_row(
            conn,
            teacher_id=teacher_id,
            subject_id=subject_id,
            starts_at=starts_at,
            ends_at=ends_at,
            slot_minutes=slot_minutes,
            room=room,
            capacity=capacity,
            status='active',
            planned_topic=str(planned_topic or "").strip(),
        )


def list_availabilities(teacher_id=None, subject_id=None, status=None, starts_at_from=None):
    with _connect() as conn:
        rows = queries.list_availabilities_rows(
            conn,
            teacher_id=teacher_id,
            subject_id=subject_id,
            status=status,
            starts_at_from=starts_at_from
        )
        return [dict(row) for row in rows]


def cancel_availability(availability_id: int, *, teacher_id: int | None = None):
    with _connect() as conn:
        availability = queries.get_availability_row(conn, availability_id)
        if not availability:
            raise ValueError("Availability slot was not found.")
        if teacher_id is not None and int(availability["teacher_id"]) != int(teacher_id):
            raise PermissionError("You can only manage your own availability slots.")

        # First cancel availability itself
        queries.update_availability_status_row(conn, availability_id, 'cancelled')
        # Also cancel all active bookings associated with it
        bookings = queries.list_bookings_rows(conn, availability_id=availability_id, status='booked')
        for booking in bookings:
            queries.update_booking_status_row(conn, booking['id'], 'cancelled', teacher_note='Availability was cancelled by teacher.')
        return True


def create_booking(
    availability_id: int,
    student_row_id: int,
    student_note: str = '',
    student_topic_request: str = '',
) -> int:
    with _connect() as conn:
        availability = queries.get_availability_row(conn, availability_id)
        if not availability or availability['status'] != 'active':
            raise ValueError("This availability slot is no longer active.")

        active_bookings = queries.list_bookings_rows(conn, availability_id=availability_id, status='booked')
        if len(active_bookings) >= availability['capacity']:
            raise ValueError("This slot has reached its booking capacity.")

        # Check if this student already booked this availability
        already_booked = any(b['student_row_id'] == student_row_id for b in active_bookings)
        if already_booked:
            raise ValueError("You have already booked this slot.")

        return queries.create_booking_row(
            conn,
            availability_id=availability_id,
            teacher_id=int(availability["teacher_id"]),
            student_row_id=student_row_id,
            subject_id=availability["subject_id"],
            starts_at=availability["starts_at"],
            ends_at=availability["ends_at"],
            status='booked',
            student_note=student_note,
            teacher_note='',
            student_topic_request=str(student_topic_request or "").strip(),
        )


def list_bookings(availability_id=None, teacher_id=None, student_row_id=None, subject_id=None, status=None, starts_at_from=None):
    with _connect() as conn:
        rows = queries.list_bookings_rows(
            conn,
            availability_id=availability_id,
            teacher_id=teacher_id,
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
    student_row_id: int | None = None,
):
    valid_statuses = {'booked', 'cancelled', 'completed', 'no_show'}
    if status not in valid_statuses:
        raise ValueError(f"Invalid status. Must be one of {valid_statuses}")
    with _connect() as conn:
        booking = queries.get_booking_row(conn, booking_id)
        if not booking:
            raise ValueError("Booking was not found.")
        if teacher_id is not None and int(booking["teacher_id"]) != int(teacher_id):
            raise PermissionError("You can only manage bookings for your own office hours.")
        if student_row_id is not None and int(booking["student_row_id"]) != int(student_row_id):
            raise PermissionError("You can only manage your own bookings.")
        return queries.update_booking_status_row(conn, booking_id, status, teacher_note)
