"""Academic Director role page routes."""

from fastapi import APIRouter, Depends

from backend.render import generate_csrf, render_react_page
from backend.roles.role_home import render_role_home
from backend.roles.workspace_counts import academic_director_workspace_cards
from backend.roles.academic_director.staff_registration import create_head_of_department_account
from backend.roles.admin.services.page_service import invalidate_admin_page_context_cache
from backend.roles.admin.services.page_service import build_admin_page_context
from backend.roles.admin.services.academic_service import list_admin_academic_context
from backend.utils.context import request
from backend.utils.guards import require_role
from backend.utils.response_helpers import jsonify
from backend.utils.session import current_auth_login, current_auth_role


def register_academic_director_page_routes(app, *, render_admin_page=None):
    router = APIRouter(dependencies=[Depends(require_role("academic_director"))])

    @router.get("/academic-director", operation_id="academic_director_home")
    @router.get("/academic_director", include_in_schema=False)
    def academic_director_home():
        return render_role_home(
            "academic-director-home",
            "academic_director",
            title="Academic Director Dashboard",
            description="Groups, teachers, subjects, attendance, and academic progress.",
            cards=academic_director_workspace_cards(),
        )

    @router.get("/academic-director/teacher-academy", operation_id="academic_director_teacher_academy")
    def academic_director_teacher_academy():
        page_context = build_admin_page_context(
            admin_panel="teachers",
            admin_school="all",
            force_refresh=False,
        )
        academic_context = list_admin_academic_context()
        return render_react_page(
            "academic-director-academy",
            {
                "authLogin": current_auth_login(),
                "authRole": current_auth_role(),
                "adminMode": "academic_director",
                "adminSchool": "all",
                "adminTeachers": page_context["admin_teachers"],
                "adminTeacherAcademy": page_context["admin_teacher_academy"],
                "adminGroupOptions": page_context["admin_group_options"],
                "adminAcademicSubjects": academic_context["subjects"],
                "adminAcademicCurriculumPrograms": academic_context.get("curriculum_programs", []),
                "adminAcademicCurriculumItems": academic_context.get("curriculum_items", []),
                "csrfToken": generate_csrf(),
            },
            title="Academic Director Teacher Academy",
            description="Academic Director Teacher Academy management.",
            telegram=True,
        )

    @router.post("/academic-director/api/head-of-departments", operation_id="academic_director_create_hod")
    def academic_director_create_hod():
        created, error_message, credentials = create_head_of_department_account(
            display_name=request.form.get("hod_display_name", ""),
            subject_id=request.form.get("hod_subject_id", ""),
            created_by=current_auth_login() or "Academic Director",
        )
        if not created:
            return jsonify(
                {"ok": False, "message": error_message or "Unable to create Head of Department."},
                status_code=400,
            )
        invalidate_admin_page_context_cache()
        return jsonify(
            {
                "ok": True,
                "message": "Head of Department account created.",
                "credentials": {
                    "role": "head_of_department",
                    "login": credentials.get("login", ""),
                    "temporary_password": credentials.get("temporary_password", ""),
                    "display_name": credentials.get("display_name", ""),
                    "subject_name": credentials.get("subject_name", ""),
                },
            }
        )

    app.include_router(router)


__all__ = ["register_academic_director_page_routes"]
