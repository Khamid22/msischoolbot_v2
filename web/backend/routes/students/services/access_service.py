from .normalization_service import normalize_text
from .session_state_service import (
    current_student_full_name,
    current_student_sheet_id,
)


def is_student_owner_of_payload(student_id, payload):
    own_full_name = normalize_text(current_student_full_name())
    if own_full_name:
        payload_student = payload.get("student", {}) if isinstance(payload, dict) else {}
        payload_full_name = normalize_text(payload_student.get("fullName", ""))
        return bool(payload_full_name) and payload_full_name == own_full_name

    own_sheet_student_id = current_student_sheet_id()
    return own_sheet_student_id is not None and int(student_id) == own_sheet_student_id


__all__ = ["is_student_owner_of_payload"]
