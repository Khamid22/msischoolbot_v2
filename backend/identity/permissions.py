"""Role permission map for portal authorization decisions."""

from backend.identity.roles import normalize_role

ROLE_PERMISSIONS = {
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
    normalized_role = normalize_role(role)
    normalized_permission = str(permission or "").strip()
    if not normalized_role or not normalized_permission:
        return False
    permissions = ROLE_PERMISSIONS.get(normalized_role, set())
    return "*" in permissions or normalized_permission in permissions


def require_permission(permission):
    from backend.utils.guards import require_permission as guard_require_permission

    return guard_require_permission(permission)


__all__ = [
    "ROLE_PERMISSIONS",
    "has_permission",
    "require_permission",
]
