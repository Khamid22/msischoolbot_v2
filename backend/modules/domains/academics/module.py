"""Academics domain registration."""

from backend.application.module_spec import ModuleSpec
from backend.modules.domains.academics.subject_curriculum.job_handlers import (
    CONVERT_PRESENTATION_HANDLER,
)

MODULE = ModuleSpec(
    name="academics",
    job_handlers=(CONVERT_PRESENTATION_HANDLER,),
)

__all__ = ["MODULE"]
