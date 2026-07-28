"""Typed durable-job payloads emitted by admissions."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class AdmissionEventModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ActivationCompletedPayload(AdmissionEventModel):
    admission_id: int = Field(gt=0)
    student_id: int = Field(gt=0)
    parent_id: int = Field(gt=0)


class GenerateInvoicesPayload(AdmissionEventModel):
    run_date: date | None = None


__all__ = ["ActivationCompletedPayload", "GenerateInvoicesPayload"]
