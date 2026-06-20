from web.backend.utils.session import current_student_enrollment_id


def is_student_owner_of_payload(student_id, payload):
    """Authorize access by the authenticated student's enrollment id.

    Ownership is decided strictly by the immutable enrollment id from the
    session, never by display name: names are not unique, so a name match would
    let students with colliding names read each other's data. ``payload`` is
    accepted for signature compatibility with callers but is not trusted.
    """
    own_enrollment_id = current_student_enrollment_id()
    if own_enrollment_id is None:
        return False
    try:
        return int(student_id) == int(own_enrollment_id)
    except (TypeError, ValueError):
        return False


__all__ = ["is_student_owner_of_payload"]
