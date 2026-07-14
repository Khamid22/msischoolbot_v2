from fastapi.responses import JSONResponse
import os

from fastapi import APIRouter, Depends, Request

from backend.core.access.pages import GuardResponse
from backend.core.web.responses import redirect
from backend.core.web.request_context import request, session
from backend.core.runtime.performance import PagePerformanceTimer, log_page_performance
from backend.modules.identity.session import url_for
from backend.core.web.rendering import generate_csrf, render_react_page

from backend.internal_operations.academics.form_routes import register_academic_admin_routes
from backend.internal_operations.form_routes import register_admin_routes
from backend.internal_operations.pages.context import (
    build_admin_page_context,
    build_edit_student_page_context,
)
from backend.modules.identity.session import (
    current_auth_login,
    current_auth_role,
    current_staff_id,
)
from backend.modules.academics.groups.operations import list_admin_academic_context
from backend.modules.people.parents.service import list_linked_parents_for_student
from backend.modules.communications.announcements_service import list_announcements

FULL_ACADEMIC_BOOTSTRAP_PANELS = {
    "teachers",
    "curriculum",
    "gradebook",
    "office_hours",
    "career_growth",
}


def register_internal_operations_page_routes(
    app,
    *,
    clear_group_cache,
):
    def delete_uploaded_student_photo(photo_url):
        raw_url = str(photo_url or "").strip()
        if not raw_url:
            return
        expected_prefix = "/static/uploads/student_photos/"
        if not raw_url.startswith(expected_prefix):
            return
        file_name = os.path.basename(raw_url)
        if not file_name:
            return
        static_root = app.static_folder or os.path.join(app.root_path, "web", "static")
        uploads_dir = os.path.join(static_root, "uploads", "student_photos")
        candidate_path = os.path.join(uploads_dir, file_name)
        if os.path.isfile(candidate_path):
            try:
                os.remove(candidate_path)
            except OSError:
                return

    def render_admin_page(
        auth_error="",
        admin_notice="",
        admin_panel="overview",
        admin_teacher_edit=None,
        admin_school="all",
        admin_mode="",
    ):
        timer = PagePerformanceTimer()
        requested_panel = str(request.args.get("panel", "") or "").strip()
        requested_school = str(request.args.get("school", "") or "").strip()
        requested_mode = str(request.args.get("mode", "") or "").strip().lower()
        if requested_panel and str(admin_panel or "overview").strip().lower() == "overview":
            admin_panel = requested_panel
        if requested_school and str(admin_school or "all").strip().lower() == "all":
            admin_school = requested_school
        if not str(admin_mode or "").strip():
            admin_mode = requested_mode
        pre_context_mode = "admin"
        normalized_panel = str(admin_panel or "overview").strip().lower()
        defer_overview_lists = (
            current_auth_role() == "admin"
            and normalized_panel == "overview"
            and pre_context_mode in {"admin", "ceo"}
        )

        force_refresh = bool(
            str(auth_error or "").strip()
            or str(admin_notice or "").strip()
            or isinstance(admin_teacher_edit, dict)
        )
        page_context = build_admin_page_context(
            admin_panel=admin_panel,
            admin_school=admin_school,
            admin_teacher_edit=admin_teacher_edit,
            parent_admin_id=session.get("admin_id", 0),
            force_refresh=force_refresh,
            defer_overview_lists=defer_overview_lists,
        )
        timer.mark("admin_context_build")
        panel = page_context["panel"]
        academic_context_is_full = (
            current_auth_role() != "admin"
            or panel in FULL_ACADEMIC_BOOTSTRAP_PANELS
        )
        try:
            academic_context = list_admin_academic_context(
                include_heavy=academic_context_is_full,
                include_groups=academic_context_is_full,
            )
        except TypeError as exc:
            if "include_groups" not in str(exc):
                raise
            academic_context = list_admin_academic_context(
                include_heavy=academic_context_is_full
            )
            if not academic_context_is_full:
                academic_context = {**academic_context, "groups": []}
        timer.mark("academic_context_build")
        announcements = list_announcements()
        timer.mark("support_context_build")
        if current_auth_role() == "head_of_department":
            from backend.modules.teacher_academy.policies import filter_admin_context_for_hod_scope

            filter_admin_context_for_hod_scope(
                page_context,
                academic_context,
                role=current_auth_role(),
                account_id=session.get("account_id"),
                staff_id=current_staff_id() or 0,
            )
            timer.mark("hod_scope_filter")

        school_filter = page_context["school_filter"]
        if current_auth_role() == "admin":
            session["admin_last_panel"] = panel
            session["admin_last_school"] = school_filter

        resolved_admin_mode = "admin"

        response = render_react_page(
            "internal-operations-home",
            {
                "authLogin": current_auth_login(),
                "authRole": current_auth_role(),
                "authError": auth_error or (page_context["sync_errors"][0] if page_context["sync_errors"] else ""),
                "adminNotice": admin_notice or page_context["load_error"] or "",
                "adminPanel": panel,
                "adminMode": resolved_admin_mode,
                "adminSchool": school_filter,
                "adminStudents": page_context["admin_students"],
                "adminTeachers": page_context["admin_teachers"],
                "adminTeacherCandidates": page_context["admin_teacher_candidates"],
                "adminTeacherAcademy": page_context["admin_teacher_academy"],
                "adminComplaints": page_context["admin_complaints"],
                "adminParents": page_context["admin_parents"],
                "adminParentChildren": page_context["admin_parent_children"],
                "adminTeacherOptions": page_context["admin_teacher_options"],
                "adminGroupOptions": page_context["admin_group_options"],
                "adminTeacherEdit": page_context["admin_teacher_edit"],
                "adminTeacherEditSchool": page_context["admin_teacher_edit_school"],
                "adminSchoolOptions": page_context["admin_school_options"],
                "adminQuickStats": page_context["admin_quick_stats"],
                "adminSchoolInfo": page_context["admin_school_info"],
                "adminSubjectInfo": page_context["admin_subject_info"],
                "adminGroupZones": page_context["admin_group_zones"],
                "adminResourceTypes": page_context["admin_resource_types"],
                "adminResourceActiveTypes": page_context["admin_resource_active_types"],
                "adminResources": page_context["admin_resources"],
                "adminResourceSubjectOptions": page_context["admin_resource_subject_options"],
                "adminResourceUploadEnabled": page_context["admin_resource_upload_enabled"],
                "adminAcademicSchools": academic_context["schools"],
                "adminAcademicSubjects": academic_context["subjects"],
                "adminAcademicGroups": academic_context["groups"],
                "adminAcademicEnrollments": academic_context.get("enrollments", []),
                "adminAcademicLessons": academic_context.get("lessons", []),
                "adminAcademicSchedules": academic_context.get("schedules", []),
                "adminAcademicSessions": academic_context.get("sessions", []),
                "adminAcademicCurriculumPrograms": academic_context.get("curriculum_programs", []),
                "adminAcademicCurriculumItems": academic_context.get("curriculum_items", []),
                "adminAcademicEnrollmentSummary": academic_context.get("enrollment_summary", {}),
                "adminAcademicContextMode": "full" if academic_context_is_full else "summary",
                "adminAnnouncements": announcements,
                "csrfToken": generate_csrf(),
            },
            title="MSI Admin Panel",
            description="Admin panel for school performance, teachers, students, and resources.",
            telegram=True,
        )
        timer.mark("render")
        log_page_performance(
            "admin_home",
            timer,
            response=response,
            rows={
                "admin_students": page_context["admin_students"],
                "admin_teachers": page_context["admin_teachers"],
                "admin_teacher_candidates": page_context["admin_teacher_candidates"],
                "admin_teacher_academy": page_context["admin_teacher_academy"],
                "admin_complaints": page_context["admin_complaints"],
                "admin_parents": page_context["admin_parents"],
                "admin_parent_children": page_context["admin_parent_children"],
                "admin_group_options": page_context["admin_group_options"],
                "academic_subjects": academic_context["subjects"],
                "academic_groups": academic_context["groups"],
                "academic_enrollments": academic_context.get("enrollments", []),
                "academic_lessons": academic_context.get("lessons", []),
                "academic_schedules": academic_context.get("schedules", []),
                "academic_sessions": academic_context.get("sessions", []),
                "curriculum_programs": academic_context.get("curriculum_programs", []),
                "curriculum_items": academic_context.get("curriculum_items", []),
                "announcements": announcements,
            },
        )
        return response

    def render_edit_student_page(student_row_id, auth_error="", admin_notice=""):
        context = build_edit_student_page_context(student_row_id)
        if not context:
            return None

        back_url = url_for("student.home", panel="students")
        return render_react_page(
            "internal-edit-student",
            {
                "authLogin": current_auth_login(),
                "authError": auth_error,
                "adminNotice": admin_notice,
                "student": context["student"],
                "teacherNameOptions": context["teacher_name_options"],
                "csrfToken": generate_csrf(),
                "saveUrl": url_for("admin.save_admin_student_profile", student_row_id=student_row_id),
                "changePasswordUrl": url_for("admin.admin_change_student_password_route", student_row_id=student_row_id),
                "parentInviteApiUrl": f"/api/v1/admin/students/{student_row_id}/parent-invite",
                "linkedParents": list_linked_parents_for_student(student_row_id),
                "viewDashboardUrl": url_for("admin.admin_student_dashboard", student_row_id=student_row_id),
                "backUrl": back_url,
                "embedMode": request.args.get("embed", "").strip(),
            },
            title="Edit Student Profile",
            description="Edit student profile details.",
            telegram=True,
            back_mode="history",
            back_url=back_url,
        )

    def ensure_admin_role(request_obj: Request):
        if current_auth_role() == "admin":
            return
        requested_with = str(request_obj.headers.get("X-Requested-With", "")).strip()
        if requested_with == "XMLHttpRequest":
            raise GuardResponse(
                JSONResponse({"ok": False, "message": "Admin authentication required."}, status_code=401)
            )
        raise GuardResponse(redirect(url_for("student.home")))

    admin_routes = APIRouter(dependencies=[Depends(ensure_admin_role)])

    @admin_routes.get(
        "/internal/operations",
        operation_id="internal_operations_home",
    )
    def internal_operations_home():
        return render_admin_page(
            admin_panel=str(request.args.get("panel") or "overview"),
            admin_school=str(request.args.get("school") or "all"),
            admin_mode=str(request.args.get("mode") or ""),
        )

    register_academic_admin_routes(
        admin_routes,
        render_admin_page=render_admin_page,
        clear_group_cache=clear_group_cache,
    )

    register_admin_routes(
        admin_routes,
        render_admin_page=render_admin_page,
        render_edit_student_page=render_edit_student_page,
        delete_uploaded_student_photo=delete_uploaded_student_photo,
    )
    app.include_router(admin_routes)
    return render_admin_page
