"""Shared request and response contracts for communication APIs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class CreateAnnouncementRequest(BaseModel):
    title: str = ""
    body: str = ""
    audience: str = "all"
    priority: str = "info"
    status: str = "draft"
    pinned: bool = False
    scheduled_at: str = ""


class UpdateAnnouncementRequest(BaseModel):
    title: str | None = None
    body: str | None = None
    audience: str | None = None
    priority: str | None = None
    status: str | None = None
    pinned: bool | None = None
    scheduled_at: str | None = None


class BlockStudentRequest(BaseModel):
    studentId: str = ""
    reason: str = ""


class AdminChatMessages(BaseModel):
    messages: list[dict[str, Any]]
    room: str


class BlockedStudents(BaseModel):
    blocked: list[dict[str, Any]]


class ChatRooms(BaseModel):
    rooms: list[dict[str, Any]]
