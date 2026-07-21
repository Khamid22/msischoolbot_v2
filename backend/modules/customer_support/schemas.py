"""API contracts for Customer Support records."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CreateStudentRequest(BaseModel):
    fullName: str = Field(min_length=2, max_length=180)
    schoolId: int = Field(gt=0)
    phone: str = Field(default="", max_length=80)
    photoUrl: str = Field(default="", max_length=1000)
    profileDescription: str = Field(default="", max_length=2000)


class UpdateStudentRequest(BaseModel):
    expectedVersion: int = Field(gt=0)
    fullName: str | None = Field(default=None, min_length=2, max_length=180)
    schoolId: int | None = Field(default=None, gt=0)
    phone: str | None = Field(default=None, max_length=80)
    photoUrl: str | None = Field(default=None, max_length=1000)
    profileDescription: str | None = Field(default=None, max_length=2000)
    status: str | None = None
    reason: str = Field(default="", max_length=1000)


class LifecycleRequest(BaseModel):
    expectedVersion: int = Field(gt=0)
    reason: str = Field(min_length=2, max_length=1000)


class VersionOnlyRequest(BaseModel):
    expectedVersion: int = Field(gt=0)


class UpdateParentRequest(BaseModel):
    expectedVersion: int = Field(gt=0)
    displayName: str | None = Field(default=None, min_length=2, max_length=180)
    phone: str | None = Field(default=None, max_length=80)
    telegramUsername: str | None = Field(default=None, max_length=80)
    preferredLanguage: str | None = None
    reason: str = Field(default="", max_length=1000)


class ParentChildRequest(BaseModel):
    studentId: int = Field(gt=0)
    expectedVersion: int = Field(gt=0)


class CreatePaymentRequest(BaseModel):
    expectedVersion: int = Field(gt=0)
    subjectId: int = Field(gt=0)
    monthLabel: str = Field(default="", max_length=120)
    amount: float = Field(gt=0)
    currency: str = Field(default="UZS", min_length=3, max_length=3)
    dueDate: str = ""
    paidAt: str = ""
    notes: str = Field(default="", max_length=2000)


class UpdatePaymentRequest(BaseModel):
    expectedVersion: int = Field(gt=0)
    monthLabel: str | None = Field(default=None, max_length=120)
    amount: float | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    dueDate: str | None = None
    notes: str | None = Field(default=None, max_length=2000)
    reason: str = Field(default="", max_length=1000)


class SettlementRequest(BaseModel):
    expectedVersion: int = Field(gt=0)
    paid: bool
    paidAt: str = ""
    reason: str = Field(default="", max_length=1000)


class VoidPaymentRequest(BaseModel):
    expectedVersion: int = Field(gt=0)
    reason: str = Field(min_length=2, max_length=1000)


__all__ = [name for name in globals() if name.endswith("Request")]
