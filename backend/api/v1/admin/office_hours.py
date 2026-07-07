"""Admin office-hours API v1 routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.api import ApiSuccess, api_success
from backend.api.v1.admin.schemas import (
    AdminCreateAvailabilityRequest,
    AvailabilityCreated,
    AvailabilityList,
    BookingList,
    CancelAvailabilityRequest,
    UpdateBookingStatusRequest,
)
from backend.domains.office_hours import service as oh_service

router = APIRouter(prefix="/office-hours")


@router.get(
    "/availability",
    operation_id="api_v1_admin_list_availability",
    response_model=ApiSuccess[AvailabilityList],
)
def list_availability(
    teacher_id: int | None = None,
    subject_id: int | None = None,
    status: str | None = None,
    starts_at_from: str | None = None,
):
    availabilities = oh_service.list_availabilities(
        teacher_id=teacher_id,
        subject_id=subject_id,
        status=status,
        starts_at_from=starts_at_from,
    )
    return api_success({"availabilities": availabilities})


@router.post(
    "/availability",
    operation_id="api_v1_admin_create_availability",
    response_model=ApiSuccess[AvailabilityCreated],
)
def create_availability(payload: AdminCreateAvailabilityRequest):
    try:
        availability_id = oh_service.create_availability(
            teacher_id=payload.teacher_id,
            subject_id=payload.subject_id,
            starts_at=payload.starts_at,
            ends_at=payload.ends_at,
            slot_minutes=payload.slot_minutes,
            room=payload.room,
            capacity=payload.capacity,
            planned_topic=payload.planned_topic.strip(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return api_success({"availability_id": availability_id})


@router.patch(
    "/availability/{availability_id}",
    operation_id="api_v1_admin_cancel_availability",
    response_model=ApiSuccess[None],
)
def cancel_availability(availability_id: int, payload: CancelAvailabilityRequest):
    if payload.status != "cancelled":
        raise HTTPException(status_code=400, detail="Only 'cancelled' state transitions are allowed.")
    try:
        oh_service.cancel_availability(availability_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return api_success()


@router.get(
    "/bookings",
    operation_id="api_v1_admin_list_bookings",
    response_model=ApiSuccess[BookingList],
)
def list_bookings(
    availability_id: int | None = None,
    teacher_id: int | None = None,
    student_row_id: int | None = None,
    subject_id: int | None = None,
    status: str | None = None,
    starts_at_from: str | None = None,
):
    bookings = oh_service.list_bookings(
        availability_id=availability_id,
        teacher_id=teacher_id,
        student_row_id=student_row_id,
        subject_id=subject_id,
        status=status,
        starts_at_from=starts_at_from,
    )
    return api_success({"bookings": bookings})


@router.patch(
    "/bookings/{booking_id}",
    operation_id="api_v1_admin_update_booking_status",
    response_model=ApiSuccess[None],
)
def update_booking_status(booking_id: int, payload: UpdateBookingStatusRequest):
    if not payload.status:
        raise HTTPException(status_code=400, detail="Missing status parameter.")
    try:
        oh_service.update_booking_status(booking_id, payload.status, payload.teacher_note)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return api_success()
