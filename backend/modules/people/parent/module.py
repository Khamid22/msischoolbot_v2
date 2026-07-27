"""Parent module metadata and default scope."""

from backend.application.module_spec import build_person_module_spec
from backend.core.access.domain_types import Role

PERSON_MODULE = build_person_module_spec(Role.PARENT)

__all__ = ["PERSON_MODULE"]
