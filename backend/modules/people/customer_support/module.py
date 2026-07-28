"""Customer Support module metadata and default scope."""

from __future__ import annotations

from dataclasses import dataclass

from backend.application.module_spec import build_person_module_spec
from backend.core.access.domain_types import (
    Capability,
    Domain,
    ObjectScope,
    Role,
    SchoolScopeMode,
)
from backend.modules.people.customer_support.domain_types import CustomerSupportSection

PERSON_MODULE = build_person_module_spec(Role.CUSTOMER_SUPPORT)


@dataclass(frozen=True)
class CustomerSupportCapabilitySpec:
    section: CustomerSupportSection
    read_capabilities: frozenset[Capability]
    write_capabilities: frozenset[Capability]
    allowed_domains: frozenset[Domain]
    school_scope_mode: SchoolScopeMode = SchoolScopeMode.ASSIGNED_SCHOOLS
    object_scope: ObjectScope = ObjectScope.SUPPORTED_PEOPLE


CUSTOMER_SUPPORT_CAPABILITIES = (
    CustomerSupportCapabilitySpec(
        section=CustomerSupportSection.ADMISSIONS,
        read_capabilities=frozenset({Capability.MANAGE_ADMISSIONS}),
        write_capabilities=frozenset(
            {
                Capability.MANAGE_ADMISSIONS,
                Capability.MANAGE_PAYMENTS,
                Capability.MANAGE_STUDENT_RECORDS,
                Capability.MANAGE_PARENT_RECORDS,
            }
        ),
        allowed_domains=frozenset(
            {
                Domain.ADMISSIONS,
                Domain.ACADEMICS,
                Domain.COMMUNICATIONS,
                Domain.FINANCE,
                Domain.IDENTITY,
                Domain.ORGANIZATION,
                Domain.PARENT_RELATIONSHIPS,
                Domain.STUDENT_RECORDS,
            }
        ),
    ),
    CustomerSupportCapabilitySpec(
        section=CustomerSupportSection.PAYMENTS,
        read_capabilities=frozenset({Capability.MANAGE_PAYMENTS}),
        write_capabilities=frozenset({Capability.MANAGE_PAYMENTS}),
        allowed_domains=frozenset(
            {
                Domain.ADMISSIONS,
                Domain.FINANCE,
                Domain.ORGANIZATION,
                Domain.STUDENT_RECORDS,
            }
        ),
    ),
    CustomerSupportCapabilitySpec(
        section=CustomerSupportSection.DASHBOARD,
        read_capabilities=frozenset({Capability.VIEW_DASHBOARD}),
        write_capabilities=frozenset(),
        allowed_domains=frozenset({Domain.REPORTING}),
    ),
    CustomerSupportCapabilitySpec(
        section=CustomerSupportSection.PARENTS,
        read_capabilities=frozenset({Capability.VIEW_PARENT_CONTACTS}),
        write_capabilities=frozenset({Capability.MANAGE_PARENT_RECORDS}),
        allowed_domains=frozenset(
            {
                Domain.IDENTITY,
                Domain.ORGANIZATION,
                Domain.PARENT_RELATIONSHIPS,
                Domain.STUDENT_RECORDS,
                Domain.FINANCE,
                Domain.SUPPORT_CASES,
            }
        ),
    ),
    CustomerSupportCapabilitySpec(
        section=CustomerSupportSection.TEACHERS,
        read_capabilities=frozenset({Capability.VIEW_TEACHER_SUPPORT_INFO}),
        write_capabilities=frozenset(),
        allowed_domains=frozenset(
            {
                Domain.IDENTITY,
                Domain.ORGANIZATION,
                Domain.TEACHER_RECORDS,
                Domain.SUPPORT_CASES,
            }
        ),
    ),
    CustomerSupportCapabilitySpec(
        section=CustomerSupportSection.TICKETS,
        read_capabilities=frozenset({Capability.VIEW_TICKETS}),
        write_capabilities=frozenset(
            {
                Capability.REPLY_TICKETS,
                Capability.ASSIGN_TICKETS,
                Capability.ESCALATE_TICKETS,
                Capability.RESOLVE_TICKETS,
            }
        ),
        allowed_domains=frozenset(
            {
                Domain.IDENTITY,
                Domain.ORGANIZATION,
                Domain.STUDENT_RECORDS,
                Domain.PARENT_RELATIONSHIPS,
                Domain.TEACHER_RECORDS,
                Domain.SUPPORT_CASES,
            }
        ),
    ),
)


__all__ = [
    "CUSTOMER_SUPPORT_CAPABILITIES",
    "PERSON_MODULE",
    "CustomerSupportCapabilitySpec",
]
