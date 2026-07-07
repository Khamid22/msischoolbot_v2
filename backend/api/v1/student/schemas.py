"""Student API v1 schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class SendChatMessageRequest(BaseModel):
    room: str = "global"
    body: str = ""


class EditChatMessageRequest(BaseModel):
    body: str = ""


class ChatMessageList(BaseModel):
    messages: list[dict[str, Any]]
    room: str


class ChatMessageSent(BaseModel):
    message: dict[str, Any]


class ChatMessageEdited(BaseModel):
    id: int
    body: str
    editedAt: str


class ChatMessageDeleted(BaseModel):
    deleted: bool
    id: int


class CreateBookingRequest(BaseModel):
    availability_id: int
    student_note: str = ""
    student_topic_request: str = ""


class CancelBookingRequest(BaseModel):
    status: str


class BookingCreated(BaseModel):
    booking_id: int


class AvailabilityList(BaseModel):
    availabilities: list[dict[str, Any]]


class BookingList(BaseModel):
    bookings: list[dict[str, Any]]


class PostCommentRequest(BaseModel):
    body: str = ""


class CommentList(BaseModel):
    comments: list[dict[str, Any]]


class CommentPosted(BaseModel):
    comment: dict[str, Any]
