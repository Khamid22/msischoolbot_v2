"""Shared payload loading and ownership checks for student-facing pages."""

from .access import is_student_owner_of_payload
from backend.modules.academics.gradebook.rating import load_dashboard_payload
from backend.core.session import (
    current_auth_role,
    current_parent_id,
    current_student_enrollment_id,
    current_student_full_name,
)
from backend.modules.people.parents.service import parent_can_access_dashboard


def load_student_payload_for_view(
    *,
    student_id,
    requested_subject,
    requested_group,
    requested_school,
    force_refresh,
    missing_message,
    session_invalid_message,
    forbidden_message,
):
    payload, dataset, payload_error = load_dashboard_payload(
        student_id=student_id,
        requested_subject=requested_subject,
        requested_group=requested_group,
        requested_school=requested_school,
        force_refresh=force_refresh,
    )
    if payload_error:
        return None, dataset, payload_error, 503
    if not payload:
        return None, dataset, missing_message, 404

    role = current_auth_role()
    if role == "student":
        if not is_student_owner_of_payload(student_id, payload):
            if not current_student_enrollment_id() and not current_student_full_name():
                return None, dataset, session_invalid_message, 401
            return None, dataset, forbidden_message, 403
    elif role == "parent":
        parent_id = current_parent_id()
        if not parent_id:
            return None, dataset, "Parent session is invalid. Please open the mini app again.", 401
        if not parent_can_access_dashboard(parent_id, student_id):
            return None, dataset, "Access denied: this student is not linked to your parent account.", 403
    elif role == "admin":
        # System-admin student previews are an explicit operational workflow.
        # Other roles must use a scoped domain endpoint instead of falling
        # through to an unrestricted student dashboard.
        pass
    elif not role:
        return None, dataset, session_invalid_message, 401
    else:
        return None, dataset, "Access denied: this role cannot open student dashboards.", 403

    return payload, dataset, "", 200


__all__ = ["load_student_payload_for_view"]
