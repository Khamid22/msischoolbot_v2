"""Request and response contracts for system-admin complaint routes."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class CreateComplaintRequest(BaseModel):
    parent_admin_id: int | None = None
    student_row_id: int | None = None
    student_id: int | None = None
    category: str = "other"
    topic: str = ""
    message: str = ""


class UpdateComplaintRequest(BaseModel):
    status: str | None = None
    reply: str | None = None
    assigned_to: str | None = None


class ComplaintReplyRequest(BaseModel):
    body: str | None = None
    reply: str | None = None
    status: str | None = None
    assigned_to: str | None = None


class ComplaintPayload(BaseModel):
    complaint: dict[str, Any]


class ComplaintList(BaseModel):
    complaints: list[dict[str, Any]]
