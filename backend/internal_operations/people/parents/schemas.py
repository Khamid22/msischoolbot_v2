"""Request and response contracts for system-admin parent routes."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class AssignParentChildRequest(BaseModel):
    student_row_id: int | None = None
    student_id: int | None = None
    parent_admin_id: int | None = None


class ParentChildAssigned(BaseModel):
    child: dict[str, Any]
