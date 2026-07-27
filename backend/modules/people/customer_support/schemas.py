"""API contracts for Customer Support records.

Python uses snake_case while ``ApiModel`` preserves the existing camelCase JSON
contract consumed by the frontend.
"""

from __future__ import annotations

from pydantic import Field

from backend.core.api import ApiModel


class CreateStudentRequest(ApiModel):
    full_name: str = Field(min_length=2, max_length=180)
    school_id: int = Field(gt=0)
    phone: str = Field(default="", max_length=80)
    photo_url: str = Field(default="", max_length=1000)
    profile_description: str = Field(default="", max_length=2000)


class UpdateStudentRequest(ApiModel):
    expected_version: int = Field(gt=0)
    full_name: str | None = Field(default=None, min_length=2, max_length=180)
    school_id: int | None = Field(default=None, gt=0)
    phone: str | None = Field(default=None, max_length=80)
    photo_url: str | None = Field(default=None, max_length=1000)
    profile_description: str | None = Field(default=None, max_length=2000)
    status: str | None = None
    reason: str = Field(default="", max_length=1000)


class LifecycleRequest(ApiModel):
    expected_version: int = Field(gt=0)
    reason: str = Field(min_length=2, max_length=1000)


class VersionOnlyRequest(ApiModel):
    expected_version: int = Field(gt=0)


class UpdateParentRequest(ApiModel):
    expected_version: int = Field(gt=0)
    display_name: str | None = Field(default=None, min_length=2, max_length=180)
    phone: str | None = Field(default=None, max_length=80)
    telegram_username: str | None = Field(default=None, max_length=80)
    preferred_language: str | None = None
    reason: str = Field(default="", max_length=1000)


class ParentChildRequest(ApiModel):
    student_id: int = Field(gt=0)
    expected_version: int = Field(gt=0)


class CreatePaymentRequest(ApiModel):
    expected_version: int = Field(gt=0)
    subject_id: int = Field(gt=0)
    month_label: str = Field(default="", max_length=120)
    amount: float = Field(gt=0)
    currency: str = Field(default="UZS", min_length=3, max_length=3)
    due_date: str = ""
    paid_at: str = ""
    notes: str = Field(default="", max_length=2000)


class UpdatePaymentRequest(ApiModel):
    expected_version: int = Field(gt=0)
    month_label: str | None = Field(default=None, max_length=120)
    amount: float | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    due_date: str | None = None
    notes: str | None = Field(default=None, max_length=2000)
    reason: str = Field(default="", max_length=1000)


class SettlementRequest(ApiModel):
    expected_version: int = Field(gt=0)
    paid: bool
    paid_at: str = ""
    reason: str = Field(default="", max_length=1000)


class VoidPaymentRequest(ApiModel):
    expected_version: int = Field(gt=0)
    reason: str = Field(min_length=2, max_length=1000)


__all__ = [name for name in globals() if name.endswith("Request")]
