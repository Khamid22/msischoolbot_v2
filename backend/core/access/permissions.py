"""Permission definitions and role-permission mappings."""

from backend.core.access import roles

# Define permission constants
PERMISSION_VIEW_DASHBOARD = "view_dashboard"
PERMISSION_MANAGE_STUDENTS = "manage_students"
PERMISSION_MANAGE_TEACHERS = "manage_teachers"
PERMISSION_MANAGE_PARENTS = "manage_parents"
PERMISSION_MANAGE_ANNOUNCEMENTS = "manage_announcements"
PERMISSION_MANAGE_RESOURCES = "manage_resources"
PERMISSION_MANAGE_COMPLAINTS = "manage_complaints"
PERMISSION_MANAGE_PAYMENTS = "manage_payments"
PERMISSION_MANAGE_ACADEMICS = "manage_academics"
PERMISSION_SYSTEM_SETTINGS = "system_settings"

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
    PERMISSION_SYSTEM_SETTINGS,
}

# Role-to-permissions mapping
ROLE_PERMISSIONS = {
    roles.ROLE_OWNER: ALL_PERMISSIONS,
    roles.ROLE_SYSTEM_ADMIN: ALL_PERMISSIONS,
    roles.ROLE_CEO: {
        PERMISSION_VIEW_DASHBOARD,
        PERMISSION_MANAGE_STUDENTS,
        PERMISSION_MANAGE_PARENTS,
        PERMISSION_MANAGE_ANNOUNCEMENTS,
        PERMISSION_MANAGE_RESOURCES,
        PERMISSION_MANAGE_COMPLAINTS,
        PERMISSION_MANAGE_PAYMENTS,
    },
    roles.ROLE_ADMIN: {
        PERMISSION_VIEW_DASHBOARD,
        PERMISSION_MANAGE_STUDENTS,
        PERMISSION_MANAGE_TEACHERS,
        PERMISSION_MANAGE_PARENTS,
        PERMISSION_MANAGE_ANNOUNCEMENTS,
        PERMISSION_MANAGE_RESOURCES,
        PERMISSION_MANAGE_COMPLAINTS,
        PERMISSION_MANAGE_PAYMENTS,
        PERMISSION_MANAGE_ACADEMICS,
    },
    roles.ROLE_TEACHER: {
        PERMISSION_VIEW_DASHBOARD,
        PERMISSION_MANAGE_RESOURCES,
        PERMISSION_MANAGE_ACADEMICS,
    },
    roles.ROLE_HR_MANAGER: {
        PERMISSION_VIEW_DASHBOARD,
        PERMISSION_MANAGE_TEACHERS,
    },
    roles.ROLE_ACADEMIC_DIRECTOR: {
        PERMISSION_VIEW_DASHBOARD,
        PERMISSION_MANAGE_TEACHERS,
        PERMISSION_MANAGE_RESOURCES,
        PERMISSION_MANAGE_ACADEMICS,
        PERMISSION_MANAGE_STUDENTS,
    },
    roles.ROLE_HEAD_OF_DEPARTMENT: {
        PERMISSION_VIEW_DASHBOARD,
        PERMISSION_MANAGE_TEACHERS,
        PERMISSION_MANAGE_ACADEMICS,
    },
    roles.ROLE_CUSTOMER_SUPPORT: {
        PERMISSION_VIEW_DASHBOARD,
        PERMISSION_MANAGE_COMPLAINTS,
    },
    roles.ROLE_PARENT: {
        PERMISSION_VIEW_DASHBOARD,
    },
    roles.ROLE_STUDENT: {
        PERMISSION_VIEW_DASHBOARD,
    },
}


def role_has_permission(role: str, permission: str) -> bool:
    """Checks if a normalized role has the specified permission."""
    norm_role = roles.normalize_role(role)
    allowed = ROLE_PERMISSIONS.get(norm_role, set())
    return permission in allowed


# Fine-grained feature permissions used by page-route guards. A separate
# vocabulary from the module-level PERMISSION_* constants above: these gate
# individual portal features, not whole management areas.
ROLE_FEATURE_PERMISSIONS = {
    "admin": {"*"},
    "system_admin": {"*"},
    "ceo": {
        "view_global_reports",
        "view_finance_summary",
        "view_school_performance",
        "view_staff_summary",
    },
    "hr_manager": {
        "manage_candidates",
        "view_candidates",
        "manage_interviews",
        "manage_teacher_academy",
        "view_teacher_profiles",
    },
    "customer_support": {
        "view_tickets",
        "reply_tickets",
        "view_parent_contacts",
        "view_student_basic_info",
    },
    "student": {
        "view_own_dashboard",
        "view_own_attendance",
        "view_own_grades",
        "view_resources",
        "use_student_chat",
    },
    "teacher": {
        "view_assigned_groups",
        "manage_attendance",
        "submit_grades",
        "view_resources",
        "write_student_comments",
    },
    "parent": {
        "view_child_progress",
        "view_child_attendance",
        "view_child_grades",
        "view_payments",
        "contact_support",
    },
    "academic_director": {
        "view_academic_reports",
        "view_teacher_performance",
        "observe_lessons",
        "manage_curriculum_progress",
        "review_demo_lessons",
    },
    "head_of_department": {
        "view_teacher_performance",
        "observe_lessons",
        "manage_teacher_academy",
        "view_teacher_profiles",
    },
}


def has_permission(role, permission) -> bool:
    """Feature-permission check against ROLE_FEATURE_PERMISSIONS ("*" = all)."""
    normalized_role = roles.normalize_role(role)
    normalized_permission = str(permission or "").strip()
    if not normalized_role or not normalized_permission:
        return False
    allowed = ROLE_FEATURE_PERMISSIONS.get(normalized_role, set())
    return "*" in allowed or normalized_permission in allowed
