"""Finance domain registration."""

from backend.application.module_spec import ModuleSpec
from backend.modules.domains.finance.job_handlers import GENERATE_INVOICES_HANDLER

MODULE = ModuleSpec(
    name="finance",
    job_handlers=(GENERATE_INVOICES_HANDLER,),
)

__all__ = ["MODULE"]
