"""Fine-grained feature permissions used by browser workspace guards."""

from backend.core.access import roles


ROLE_FEATURE_PERMISSIONS = {
    "ceo": {
        "view_global_reports",
        "view_finance_summary",
        "view_school_performance",
        "view_staff_summary",
        "view_recruitment",
        "finalize_recruitment",
    },
    "customer_support": {
        "view_tickets",
        "reply_tickets",
        "view_parent_contacts",
        "view_student_basic_info",
        "manage_student_records",
        "manage_parent_records",
        "manage_student_access",
        "manage_payments",
    },
    "student": {
        "view_own_dashboard",
        "view_own_attendance",
        "view_own_grades",
        "view_resources",
        "use_student_chat",
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
        "view_recruitment",
        "evaluate_recruitment_candidates",
    },
    "head_of_department": {
        "view_teacher_performance",
        "observe_lessons",
        "manage_teacher_academy",
        "view_teacher_profiles",
        "view_recruitment",
        "evaluate_recruitment_candidates",
    },
    "hr_manager": {
        "view_recruitment",
        "manage_recruitment",
    },
}


def has_workspace_permission(role, permission) -> bool:
    normalized_role = roles.normalize_role(role)
    normalized_permission = str(permission or "").strip()
    if not normalized_role or not normalized_permission:
        return False
    allowed = ROLE_FEATURE_PERMISSIONS.get(normalized_role, set())
    return "*" in allowed or normalized_permission in allowed
