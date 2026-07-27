"""Teacher Academy module registration."""

from backend.application.module_spec import ModuleSpec
from backend.modules.domains.teacher_academy.job_handlers import SEND_NOTIFICATION_HANDLER

MODULE = ModuleSpec(
    name="teacher_academy",
    job_handlers=(SEND_NOTIFICATION_HANDLER,),
)


__all__ = ["MODULE"]
