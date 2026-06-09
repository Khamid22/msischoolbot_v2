"""Shared payload loading and ownership checks for student-facing pages."""

from .access_service import is_student_owner_of_payload
from .session_state_service import (
    current_auth_role,
    current_student_full_name,
    current_student_sheet_id,
)


def load_student_payload_for_view(
    *,
    student_id,
    requested_subject,
    requested_group,
    requested_school,
    force_refresh,
    load_dashboard_payload,
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

    if current_auth_role() == "student" and not is_student_owner_of_payload(
        student_id,
        payload,
    ):
        if not current_student_sheet_id() and not current_student_full_name():
            return None, dataset, session_invalid_message, 401
        return None, dataset, forbidden_message, 403

    return payload, dataset, "", 200


__all__ = ["load_student_payload_for_view"]
