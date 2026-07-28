"""One capability registry shared by API and browser workspace guards."""

from __future__ import annotations

from dataclasses import dataclass

from backend.core.access.domain_types import (
    Capability,
    Domain,
    ObjectScope,
    Role,
    SchoolScopeMode,
)


@dataclass(frozen=True)
class PersonAccessDefaults:
    capabilities: frozenset[Capability]
    allowed_domains: frozenset[Domain]
    school_scope_mode: SchoolScopeMode
    object_scope: ObjectScope


PERSON_ACCESS_DEFAULTS: dict[Role, PersonAccessDefaults] = {
    Role.CEO: PersonAccessDefaults(
        capabilities=frozenset(
            {
                Capability.VIEW_DASHBOARD,
                Capability.MANAGE_STUDENTS,
                Capability.MANAGE_PARENTS,
                Capability.MANAGE_ANNOUNCEMENTS,
                Capability.MANAGE_RESOURCES,
                Capability.MANAGE_COMPLAINTS,
                Capability.MANAGE_PAYMENTS,
                Capability.MANAGE_ADMISSIONS,
                Capability.MANAGE_RECRUITMENT,
                Capability.VIEW_GLOBAL_REPORTS,
                Capability.VIEW_FINANCE_SUMMARY,
                Capability.VIEW_SCHOOL_PERFORMANCE,
                Capability.VIEW_STAFF_SUMMARY,
                Capability.VIEW_RECRUITMENT,
                Capability.FINALIZE_RECRUITMENT,
            }
        ),
        allowed_domains=frozenset(
            {
                Domain.IDENTITY,
                Domain.ADMISSIONS,
                Domain.ORGANIZATION,
                Domain.REPORTING,
                Domain.FINANCE,
                Domain.RECRUITMENT,
                Domain.ACADEMICS,
                Domain.TEACHER_RECORDS,
                Domain.COMMUNICATIONS,
                Domain.SUPPORT_CASES,
            }
        ),
        school_scope_mode=SchoolScopeMode.ALL_SCHOOLS,
        object_scope=ObjectScope.ORGANIZATION_WIDE,
    ),
    Role.CUSTOMER_SUPPORT: PersonAccessDefaults(
        capabilities=frozenset(
            {
                Capability.VIEW_DASHBOARD,
                Capability.MANAGE_STUDENTS,
                Capability.MANAGE_PARENTS,
                Capability.MANAGE_PAYMENTS,
                Capability.MANAGE_ADMISSIONS,
                Capability.MANAGE_COMPLAINTS,
                Capability.VIEW_TICKETS,
                Capability.REPLY_TICKETS,
                Capability.ASSIGN_TICKETS,
                Capability.ESCALATE_TICKETS,
                Capability.RESOLVE_TICKETS,
                Capability.VIEW_PARENT_CONTACTS,
                Capability.VIEW_STUDENT_BASIC_INFO,
                Capability.VIEW_TEACHER_SUPPORT_INFO,
                Capability.MANAGE_STUDENT_RECORDS,
                Capability.MANAGE_PARENT_RECORDS,
                Capability.MANAGE_STUDENT_ACCESS,
            }
        ),
        allowed_domains=frozenset(
            {
                Domain.IDENTITY,
                Domain.ADMISSIONS,
                Domain.ACADEMICS,
                Domain.ORGANIZATION,
                Domain.STUDENT_RECORDS,
                Domain.PARENT_RELATIONSHIPS,
                Domain.TEACHER_RECORDS,
                Domain.FINANCE,
                Domain.SUPPORT_CASES,
                Domain.COMMUNICATIONS,
                Domain.REPORTING,
            }
        ),
        school_scope_mode=SchoolScopeMode.ASSIGNED_SCHOOLS,
        object_scope=ObjectScope.SUPPORTED_PEOPLE,
    ),
    Role.STUDENT: PersonAccessDefaults(
        capabilities=frozenset(
            {
                Capability.VIEW_DASHBOARD,
                Capability.VIEW_OWN_DASHBOARD,
                Capability.VIEW_OWN_ATTENDANCE,
                Capability.VIEW_OWN_GRADES,
                Capability.VIEW_RESOURCES,
                Capability.VIEW_PAYMENTS,
                Capability.CONTACT_SUPPORT,
                Capability.USE_STUDENT_CHAT,
            }
        ),
        allowed_domains=frozenset(
            {
                Domain.IDENTITY,
                Domain.ORGANIZATION,
                Domain.STUDENT_RECORDS,
                Domain.ACADEMICS,
                Domain.FINANCE,
                Domain.COMMUNICATIONS,
                Domain.SUPPORT_CASES,
                Domain.REPORTING,
            }
        ),
        school_scope_mode=SchoolScopeMode.ASSIGNED_SCHOOLS,
        object_scope=ObjectScope.OWN_RECORDS,
    ),
    Role.PARENT: PersonAccessDefaults(
        capabilities=frozenset(
            {
                Capability.VIEW_DASHBOARD,
                Capability.VIEW_CHILD_PROGRESS,
                Capability.VIEW_CHILD_ATTENDANCE,
                Capability.VIEW_CHILD_GRADES,
                Capability.VIEW_PAYMENTS,
                Capability.CONTACT_SUPPORT,
            }
        ),
        allowed_domains=frozenset(
            {
                Domain.IDENTITY,
                Domain.PARENT_RELATIONSHIPS,
                Domain.STUDENT_RECORDS,
                Domain.ACADEMICS,
                Domain.FINANCE,
                Domain.COMMUNICATIONS,
                Domain.SUPPORT_CASES,
                Domain.REPORTING,
            }
        ),
        school_scope_mode=SchoolScopeMode.ASSIGNED_SCHOOLS,
        object_scope=ObjectScope.LINKED_CHILDREN,
    ),
    Role.ACADEMIC_DIRECTOR: PersonAccessDefaults(
        capabilities=frozenset(
            {
                Capability.VIEW_DASHBOARD,
                Capability.MANAGE_TEACHERS,
                Capability.MANAGE_RESOURCES,
                Capability.MANAGE_ACADEMICS,
                Capability.MANAGE_STUDENTS,
                Capability.MANAGE_RECRUITMENT,
                Capability.VIEW_ACADEMIC_REPORTS,
                Capability.VIEW_TEACHER_PERFORMANCE,
                Capability.OBSERVE_LESSONS,
                Capability.MANAGE_CURRICULUM_PROGRESS,
                Capability.REVIEW_DEMO_LESSONS,
                Capability.VIEW_RECRUITMENT,
                Capability.EVALUATE_RECRUITMENT_CANDIDATES,
            }
        ),
        allowed_domains=frozenset(
            {
                Domain.IDENTITY,
                Domain.ORGANIZATION,
                Domain.ACADEMICS,
                Domain.STUDENT_RECORDS,
                Domain.TEACHER_RECORDS,
                Domain.TEACHER_ACADEMY,
                Domain.RECRUITMENT,
                Domain.REPORTING,
                Domain.COMMUNICATIONS,
            }
        ),
        school_scope_mode=SchoolScopeMode.ASSIGNED_SCHOOLS,
        object_scope=ObjectScope.MANAGED_ACADEMIC_RECORDS,
    ),
    Role.HEAD_OF_DEPARTMENT: PersonAccessDefaults(
        capabilities=frozenset(
            {
                Capability.VIEW_DASHBOARD,
                Capability.MANAGE_TEACHERS,
                Capability.MANAGE_ACADEMICS,
                Capability.MANAGE_RECRUITMENT,
                Capability.VIEW_TEACHER_PERFORMANCE,
                Capability.OBSERVE_LESSONS,
                Capability.MANAGE_TEACHER_ACADEMY,
                Capability.VIEW_TEACHER_PROFILES,
                Capability.VIEW_RECRUITMENT,
                Capability.EVALUATE_RECRUITMENT_CANDIDATES,
            }
        ),
        allowed_domains=frozenset(
            {
                Domain.IDENTITY,
                Domain.ORGANIZATION,
                Domain.ACADEMICS,
                Domain.TEACHER_RECORDS,
                Domain.TEACHER_ACADEMY,
                Domain.RECRUITMENT,
                Domain.REPORTING,
            }
        ),
        school_scope_mode=SchoolScopeMode.ASSIGNED_SCHOOLS,
        object_scope=ObjectScope.ASSIGNED_DEPARTMENTS_AND_SUBJECTS,
    ),
    Role.HR_MANAGER: PersonAccessDefaults(
        capabilities=frozenset(
            {
                Capability.VIEW_DASHBOARD,
                Capability.MANAGE_RECRUITMENT,
                Capability.VIEW_RECRUITMENT,
            }
        ),
        allowed_domains=frozenset(
            {
                Domain.IDENTITY,
                Domain.RECRUITMENT,
                Domain.REPORTING,
            }
        ),
        school_scope_mode=SchoolScopeMode.ASSIGNED_SCHOOLS,
        object_scope=ObjectScope.ASSIGNED_RECRUITMENT_RECORDS,
    ),
    Role.TEACHER: PersonAccessDefaults(
        capabilities=frozenset({Capability.VIEW_DASHBOARD}),
        allowed_domains=frozenset(
            {
                Domain.IDENTITY,
                Domain.ORGANIZATION,
                Domain.TEACHER_RECORDS,
                Domain.ACADEMICS,
                Domain.TEACHER_ACADEMY,
                Domain.COMMUNICATIONS,
                Domain.REPORTING,
            }
        ),
        school_scope_mode=SchoolScopeMode.ASSIGNED_SCHOOLS,
        object_scope=ObjectScope.OWN_AND_ASSIGNED_RECORDS,
    ),
}

ROLE_CAPABILITIES: dict[Role, frozenset[Capability]] = {
    role: defaults.capabilities for role, defaults in PERSON_ACCESS_DEFAULTS.items()
}


def capabilities_for_role(role: Role | str) -> frozenset[Capability]:
    try:
        normalized_role = role if isinstance(role, Role) else Role(str(role))
    except ValueError:
        return frozenset()
    return ROLE_CAPABILITIES.get(normalized_role, frozenset())


def role_has_capability(role: Role | str, capability: Capability | str) -> bool:
    try:
        normalized_capability = (
            capability if isinstance(capability, Capability) else Capability(str(capability))
        )
    except ValueError:
        return False
    return normalized_capability in capabilities_for_role(role)


def access_defaults_for_role(role: Role | str) -> PersonAccessDefaults | None:
    try:
        normalized_role = role if isinstance(role, Role) else Role(str(role))
    except ValueError:
        return None
    return PERSON_ACCESS_DEFAULTS.get(normalized_role)


__all__ = [
    "PERSON_ACCESS_DEFAULTS",
    "ROLE_CAPABILITIES",
    "PersonAccessDefaults",
    "access_defaults_for_role",
    "capabilities_for_role",
    "role_has_capability",
]
