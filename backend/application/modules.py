"""Explicit registry of product modules with application-level contributions."""

from __future__ import annotations

from backend.application.module_spec import ModuleSpec
from backend.modules.domains.academics.module import MODULE as ACADEMICS_MODULE
from backend.modules.domains.communications.module import MODULE as COMMUNICATIONS_MODULE
from backend.modules.domains.finance.module import MODULE as FINANCE_MODULE
from backend.modules.domains.identity.module import MODULE as IDENTITY_MODULE
from backend.modules.domains.organization.module import MODULE as ORGANIZATION_MODULE
from backend.modules.domains.parent_relationships.module import (
    MODULE as PARENT_RELATIONSHIPS_MODULE,
)
from backend.modules.domains.recruitment.module import MODULE as RECRUITMENT_MODULE
from backend.modules.domains.reporting.module import MODULE as REPORTING_MODULE
from backend.modules.domains.student_records.module import MODULE as STUDENT_RECORDS_MODULE
from backend.modules.domains.support_cases.module import MODULE as SUPPORT_CASES_MODULE
from backend.modules.domains.teacher_academy.module import MODULE as TEACHER_ACADEMY_MODULE
from backend.modules.domains.teacher_records.module import MODULE as TEACHER_RECORDS_MODULE
from backend.modules.jobs.handlers import JobHandlerRegistry
from backend.modules.jobs.module import MODULE as JOBS_MODULE

DOMAIN_MODULES: tuple[ModuleSpec, ...] = (
    IDENTITY_MODULE,
    ORGANIZATION_MODULE,
    STUDENT_RECORDS_MODULE,
    PARENT_RELATIONSHIPS_MODULE,
    TEACHER_RECORDS_MODULE,
    ACADEMICS_MODULE,
    RECRUITMENT_MODULE,
    TEACHER_ACADEMY_MODULE,
    FINANCE_MODULE,
    SUPPORT_CASES_MODULE,
    COMMUNICATIONS_MODULE,
    REPORTING_MODULE,
    JOBS_MODULE,
)


def build_job_handler_registry(
    modules: tuple[ModuleSpec, ...] = DOMAIN_MODULES,
) -> JobHandlerRegistry:
    registry = JobHandlerRegistry()
    for module_spec in modules:
        for handler_spec in module_spec.job_handlers:
            registry.register(handler_spec)
    return registry


__all__ = ["DOMAIN_MODULES", "build_job_handler_registry"]
