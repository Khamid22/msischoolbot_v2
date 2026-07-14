"""Student API v1 router.

Guarded by authentication only (not role): reads are available to any
signed-in session — matching the legacy behavior admin preview mode relies
on — while write handlers enforce the student role themselves.
"""

from fastapi import APIRouter, Depends, Request

from backend.modules.people.students.activity_api import router as activity_router
from backend.modules.people.students.chat_api import router as chat_router
from backend.modules.people.students.comments_api import router as comments_router
from backend.modules.people.students.office_hours_api import router as office_hours_router
from backend.modules.people.students.service import record_student_activity
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
router.include_router(chat_router)
router.include_router(comments_router)
router.include_router(office_hours_router)

__all__ = ["router"]
