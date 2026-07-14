"""Request and response contracts for system-admin student routes."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class AdminCreateStudentRequest(BaseModel):
    full_name: str
    group_id: int


class AdminStudentsList(BaseModel):
    students: list[dict[str, Any]]


class AdminStudentCreated(BaseModel):
    student: dict[str, Any]


class AdminParentInviteCreated(BaseModel):
    invite_code: str
    inviteCode: str
    invite_url: str
    inviteUrl: str
    telegram_invite_url: str
    telegramInviteUrl: str
    web_invite_url: str
    webInviteUrl: str
