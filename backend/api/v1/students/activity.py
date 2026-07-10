"""Student activity heartbeat API v1 route."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from backend.core.http import ApiSuccess, api_success
from backend.services.students.core import (
    get_student_db_id_by_enrollment_id,
    record_student_activity,
)
from backend.core.access import CurrentUser, get_current_user
from backend.core.session import current_student_school_code

router = APIRouter(prefix="/activity")


@router.get(
    "/ping",
    operation_id="api_v1_student_activity_ping",
    response_model=ApiSuccess[dict],
)
def activity_ping(request: Request, user: CurrentUser = Depends(get_current_user)):
    if user.role != "student" or user.student_db_id is None:
        raise HTTPException(status_code=401, detail="Student session is missing.")

    result = record_student_activity(user.student_db_id)
    if result.get("reason") == "student_not_found":
        # Session repair: the student row may have been recreated by a sync.
        session = request.session
        enrollment_id = user.student_enrollment_id
        school_code = current_student_school_code()
        resolved_student_db_id = get_student_db_id_by_enrollment_id(
            enrollment_id,
            school_code=school_code,
        )
        if resolved_student_db_id and resolved_student_db_id != user.student_db_id:
            session["student_db_id"] = resolved_student_db_id
            result = record_student_activity(resolved_student_db_id)

    if result.get("updated") or result.get("skipped"):
        return api_success(result)

    status_code = 404 if result.get("reason") == "student_not_found" else 500
    raise HTTPException(status_code=status_code, detail=result.get("reason") or "Activity update failed.")
