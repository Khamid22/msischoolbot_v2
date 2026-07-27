"""Student office-hours API v1 routes."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException

from backend.core.api import ApiSuccess, api_success
from backend.modules.people.student.schemas import (
    AvailabilityList,
    BookingCreated,
    BookingList,
    CancelBookingRequest,
    CreateBookingRequest,
)
from backend.modules.domains.academics import contracts as oh_service
from backend.core.access import CurrentUser, get_current_user

router = APIRouter(prefix="/office-hours")


def _require_student_db_id(user: CurrentUser) -> int:
    if not user.student_db_id:
        raise HTTPException(status_code=401, detail="Student session required.")
    return user.student_db_id


@router.get(
    "/availability",
    operation_id="api_v1_student_list_availability",
    response_model=ApiSuccess[AvailabilityList],
)
def list_availability(
    teacher_id: int | None = None,
    subject_id: int | None = None,
    starts_at_from: str | None = None,
    user: CurrentUser = Depends(get_current_user),
):
    # Students only see active availabilities
    availabilities = oh_service.list_availabilities(
        teacher_id=teacher_id,
        subject_id=subject_id,
        status="active",
        starts_at_from=starts_at_from or datetime.now(UTC).isoformat(),
    )
    return api_success({"availabilities": availabilities})


@router.get(
    "/bookings",
    operation_id="api_v1_student_list_bookings",
    response_model=ApiSuccess[BookingList],
)
def list_bookings(user: CurrentUser = Depends(get_current_user)):
    student_db_id = _require_student_db_id(user)
    bookings = oh_service.list_bookings(student_db_id=student_db_id)
    return api_success({"bookings": bookings})


@router.post(
    "/bookings",
    operation_id="api_v1_student_create_booking",
    response_model=ApiSuccess[BookingCreated],
)
def create_booking(
    payload: CreateBookingRequest,
    user: CurrentUser = Depends(get_current_user),
):
    student_db_id = _require_student_db_id(user)
    try:
        booking_id = oh_service.create_booking(
            availability_id=payload.availability_id,
            student_db_id=student_db_id,
            student_note=payload.student_note,
            student_topic_request=payload.student_topic_request.strip(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return api_success({"booking_id": booking_id})


@router.patch(
    "/bookings/{booking_id}",
    operation_id="api_v1_student_cancel_booking",
    response_model=ApiSuccess[None],
)
def cancel_booking(
    booking_id: int,
    payload: CancelBookingRequest,
    user: CurrentUser = Depends(get_current_user),
):
    if payload.status != "cancelled":
        raise HTTPException(status_code=400, detail="Only 'cancelled' state transitions are allowed.")
    student_db_id = _require_student_db_id(user)
    try:
        oh_service.update_booking_status(
            booking_id,
            "cancelled",
            "Cancelled by student.",
            student_db_id=student_db_id,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return api_success()
