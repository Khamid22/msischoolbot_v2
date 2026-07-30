"""Finance domain registration."""

from backend.application.module_spec import ModuleSpec
from backend.modules.domains.finance.job_handlers import (
    BOOTSTRAP_ENFORCEMENT_HANDLER,
    GENERATE_INVOICES_HANDLER,
    ISSUE_BILLING_CYCLE_HANDLER,
    PROCESS_ENFORCEMENT_STAGE_HANDLER,
    RECONCILE_ENFORCEMENT_HANDLER,
    SEND_BILLING_NOTIFICATION_HANDLER,
)

MODULE = ModuleSpec(
    name="finance",
    job_handlers=(
        GENERATE_INVOICES_HANDLER,
        ISSUE_BILLING_CYCLE_HANDLER,
        BOOTSTRAP_ENFORCEMENT_HANDLER,
        PROCESS_ENFORCEMENT_STAGE_HANDLER,
        SEND_BILLING_NOTIFICATION_HANDLER,
        RECONCILE_ENFORCEMENT_HANDLER,
    ),
)

__all__ = ["MODULE"]
