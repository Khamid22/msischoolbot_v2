from backend.modules.identity.session import current_student_enrollment_id


def is_student_owner_of_payload(student_id, payload):
    own_enrollment_id = current_student_enrollment_id()
    if own_enrollment_id is None:
        return False
    try:
        return int(student_id) == int(own_enrollment_id)
    except (TypeError, ValueError):
        return False


__all__ = ["is_student_owner_of_payload"]
