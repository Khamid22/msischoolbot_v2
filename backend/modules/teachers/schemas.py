"""Teacher HTTP schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class CreateAvailabilityRequest(BaseModel):
    starts_at: str
    ends_at: str
    slot_minutes: int = 30
    room: str = ""
    capacity: int = 1
    subject_id: int | None = None
    planned_topic: str = ""


class CancelAvailabilityRequest(BaseModel):
    status: str


class UpdateBookingStatusRequest(BaseModel):
    status: str
    teacher_note: str | None = None


class AvailabilityCreated(BaseModel):
    availability_id: int


class AvailabilityList(BaseModel):
    availabilities: list[dict[str, Any]]


class BookingList(BaseModel):
    bookings: list[dict[str, Any]]
