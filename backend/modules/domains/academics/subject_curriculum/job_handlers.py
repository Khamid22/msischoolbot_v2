"""Durable worker registration for curriculum presentation conversion."""

from pydantic import BaseModel, ConfigDict, Field

from backend.core.jobs import JobExecutionContext, JobHandlerSpec
from backend.modules.domains.academics.subject_curriculum.media import (
    CONVERT_PRESENTATION_TOPIC,
)
from backend.modules.domains.academics.subject_curriculum.presentation_conversion import (
    convert_presentation_asset,
)


class ConvertPresentationPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    asset_id: int = Field(ge=1)


def convert_curriculum_presentation(
    payload: ConvertPresentationPayload,
    context: JobExecutionContext,
) -> None:
    del context
    convert_presentation_asset(payload.asset_id)


CONVERT_PRESENTATION_HANDLER = JobHandlerSpec(
    topic=CONVERT_PRESENTATION_TOPIC,
    payload_model=ConvertPresentationPayload,
    handler=convert_curriculum_presentation,
)


__all__ = [
    "CONVERT_PRESENTATION_HANDLER",
    "ConvertPresentationPayload",
    "convert_curriculum_presentation",
]
