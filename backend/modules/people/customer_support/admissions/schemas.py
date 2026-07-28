"""Customer Support admission transport models."""

from pydantic import Field

from backend.core.api import ApiModel
from backend.modules.people.customer_support.admissions.contracts import (
    AdmissionDetail,
    AdmissionLink,
)


class AdmissionCreatedResponse(ApiModel):
    admission: AdmissionDetail
    admission_link: AdmissionLink
    public_url: str


class AdmissionSentResponse(ApiModel):
    admission: AdmissionDetail
    public_url: str


class AdmissionSearchStatus(ApiModel):
    status: str = Field(default="all")


__all__ = [
    "AdmissionCreatedResponse",
    "AdmissionSearchStatus",
    "AdmissionSentResponse",
]
