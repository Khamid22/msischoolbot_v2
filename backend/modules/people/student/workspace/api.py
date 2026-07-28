"""Student API v1 router.

Guarded by authentication at the router boundary. Individual handlers enforce
the student role or the relevant student/parent object policy.
"""

from fastapi import APIRouter, Depends, Request

from backend.modules.people.student.contracts import (
    activity_router,
    chat_router,
    comments_router,
    office_hours_router,
    record_student_activity,
)
from backend.modules.people.student.billing_api import router as billing_router
from backend.modules.people.student.support_api import router as support_router
from backend.core.access import get_current_user
from backend.core.access.roles import normalize_role


def track_student_activity(request: Request):
    """Record student activity on every student API call.

    The activity ping records (and repairs) activity itself, so skip it here.
    """
    if request.url.path.endswith("/activity/ping"):
        return
    session = request.session
    if normalize_role(session.get("auth_role")) != "student":
        return
    try:
        student_db_id = int(session.get("student_db_id"))
    except (TypeError, ValueError):
        return
    if student_db_id > 0:
        record_student_activity(student_db_id)


router = APIRouter(
    prefix="/student",
    dependencies=[Depends(get_current_user), Depends(track_student_activity)],
)
router.include_router(activity_router)
router.include_router(billing_router)
router.include_router(chat_router)
router.include_router(comments_router)
router.include_router(office_hours_router)
router.include_router(support_router)

__all__ = ["router"]
