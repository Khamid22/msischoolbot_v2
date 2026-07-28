"""Admission module registration."""

from backend.application.module_spec import ModuleSpec
from backend.modules.domains.admissions.job_handlers import (
    ACTIVATION_COMPLETED_HANDLER,
    GENERATE_INVOICES_HANDLER,
)

MODULE = ModuleSpec(
    name="admissions",
    job_handlers=(
        ACTIVATION_COMPLETED_HANDLER,
        GENERATE_INVOICES_HANDLER,
    ),
)

__all__ = ["MODULE"]
