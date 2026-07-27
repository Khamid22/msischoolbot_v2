"""Coarse permissions used by authenticated JSON management APIs."""

from backend.core.access import roles
from backend.core.access.capabilities import capabilities_for_role, role_has_capability
from backend.core.access.domain_types import Capability


PERMISSION_VIEW_DASHBOARD = Capability.VIEW_DASHBOARD.value
PERMISSION_MANAGE_STUDENTS = Capability.MANAGE_STUDENTS.value
PERMISSION_MANAGE_TEACHERS = Capability.MANAGE_TEACHERS.value
PERMISSION_MANAGE_PARENTS = Capability.MANAGE_PARENTS.value
PERMISSION_MANAGE_ANNOUNCEMENTS = Capability.MANAGE_ANNOUNCEMENTS.value
PERMISSION_MANAGE_RESOURCES = Capability.MANAGE_RESOURCES.value
PERMISSION_MANAGE_COMPLAINTS = Capability.MANAGE_COMPLAINTS.value
PERMISSION_MANAGE_PAYMENTS = Capability.MANAGE_PAYMENTS.value
PERMISSION_MANAGE_ACADEMICS = Capability.MANAGE_ACADEMICS.value
PERMISSION_MANAGE_RECRUITMENT = Capability.MANAGE_RECRUITMENT.value

ALL_PERMISSIONS = {
    PERMISSION_VIEW_DASHBOARD,
    PERMISSION_MANAGE_STUDENTS,
    PERMISSION_MANAGE_TEACHERS,
    PERMISSION_MANAGE_PARENTS,
    PERMISSION_MANAGE_ANNOUNCEMENTS,
    PERMISSION_MANAGE_RESOURCES,
    PERMISSION_MANAGE_COMPLAINTS,
    PERMISSION_MANAGE_PAYMENTS,
    PERMISSION_MANAGE_ACADEMICS,
    PERMISSION_MANAGE_RECRUITMENT,
}

ROLE_PERMISSIONS = {
    role: {
        capability.value
        for capability in capabilities_for_role(role)
        if capability.value in ALL_PERMISSIONS
    }
    for role in roles.ALL_ROLES
}


def role_has_permission(role: str, permission: str) -> bool:
    normalized_role = roles.normalize_role(role)
    return role_has_capability(normalized_role, permission)
