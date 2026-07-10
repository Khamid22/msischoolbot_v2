"""Teacher page adapter, scoped to the authenticated teacher."""

from fastapi.responses import JSONResponse
from backend.core.rendering import generate_csrf, render_react_page
from backend.modules.teachers.workspace import build_teacher_workspace
from backend.modules.teachers.cards import build_teacher_workspace_cards
from backend.core.web_responses import redirect
from fastapi import APIRouter, Depends, Request

from backend.core.guards import GuardResponse
from backend.core.performance import PagePerformanceTimer, log_page_performance
from backend.core.session import (
    current_auth_login,
    current_auth_role,
    current_teacher_id,
    current_teacher_staff_id,
)


def register_teacher_page_routes(app):
    def ensure_teacher_role(request_obj: Request):
        if current_auth_role() == "teacher":
            return
        requested_with = str(request_obj.headers.get("X-Requested-With", "")).strip()
        if requested_with == "XMLHttpRequest" or request_obj.url.path.startswith("/api/v1/teacher/"):
            raise GuardResponse(
                JSONResponse({"ok": False, "message": "Teacher authentication required."}, status_code=401)
            )
        raise GuardResponse(redirect("/"))

    teacher = APIRouter(dependencies=[Depends(ensure_teacher_role)])

    @teacher.get("/teacher")
    def teacher_home():
        timer = PagePerformanceTimer()
        teacher_id = current_teacher_id()
        teacher_staff_id = current_teacher_staff_id()
        try:
            workspace = build_teacher_workspace(teacher_id, teacher_staff_id)
        except Exception:
            workspace = None
        timer.mark("workspace_build")
        if not isinstance(workspace, dict):
            workspace = {
                "teacher": {
                    "id": teacher_id or 0,
                    "full_name": "",
                    "login": current_auth_login(),
                    "assigned_group": "",
                    "category": "",
                    "semester_stage": "",
                    "performance_score": 0,
                },
                "groups": [],
                "academy": None,
                "academy_summary": {},
                "academy_updates": [],
                "journey": [],
                "lesson_reports": [],
                "training_timetable": [],
            }
        workspace_cards = build_teacher_workspace_cards(
            teacher_id=teacher_id,
            teacher_staff_id=teacher_staff_id,
            workspace=workspace,
        )
        timer.mark("card_build")

        # Get teacher's DB details for academic info (subject, etc.)
        from backend.modules.teachers.service import get_teacher_by_id
        try:
            teacher_db = get_teacher_by_id(teacher_id) if teacher_id else None
        except Exception:
            teacher_db = None
        timer.mark("teacher_lookup")

        # Get list of subjects for teacher's options
        from backend.modules.teachers.service import list_subject_options_for_teacher
        try:
            subjects_options = list_subject_options_for_teacher(teacher_id) if teacher_id else []
        except Exception:
            subjects_options = []
        timer.mark("subject_options")

        response = render_react_page(
            "teacher-home",
            {
                "authLogin": current_auth_login(),
                "csrfToken": generate_csrf(),
                "teacher": {
                    **workspace["teacher"],
                    "id": teacher_id,
                    "assigned_group": teacher_db.get("assigned_group", "") if teacher_db else "",
                    "category": teacher_db.get("category", "") if teacher_db else "",
                    "semester_stage": teacher_db.get("semester_stage", "") if teacher_db else "",
                    "performance_score": teacher_db.get("performance_score", 7.0) if teacher_db else 7.0,
                },
                "groups": workspace["groups"],
                "academy": workspace.get("academy"),
                "academySummary": workspace.get("academy_summary", {}),
                "academyUpdates": workspace.get("academy_updates", []),
                "journey": workspace.get("journey", []),
                "lessonReports": workspace.get("lesson_reports", []),
                "trainingTimetable": workspace.get("training_timetable", []),
                "subjectsOptions": subjects_options,
                "workspaceCards": workspace_cards,
            },
        )
        timer.mark("render")
        log_page_performance(
            "teacher_home",
            timer,
            response=response,
            rows={
                "groups": workspace["groups"],
                "academy": [workspace.get("academy")] if workspace.get("academy") else [],
                "academy_updates": workspace.get("academy_updates", []),
                "journey": workspace.get("journey", []),
                "lesson_reports": workspace.get("lesson_reports", []),
                "training_timetable": workspace.get("training_timetable", []),
                "subjects_options": subjects_options,
                "workspace_cards": workspace_cards,
            },
        )
        return response

    app.include_router(teacher)
