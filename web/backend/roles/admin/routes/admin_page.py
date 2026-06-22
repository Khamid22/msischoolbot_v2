import os

from web.backend.utils.router import RouteGroup
from web.backend.utils.response_helpers import jsonify, redirect
from web.backend.utils.context import request, session
from web.backend.utils.session import url_for
from web.backend.render import generate_csrf, render_react_page

from web.backend.roles.admin.routes.academic_routes import register_academic_admin_routes
from web.backend.roles.admin.routes.admins import register_admin_routes
from web.backend.roles.admin.routes.announcement_routes import register_announcement_admin_routes
from web.backend.roles.admin.routes.chat_admin_routes import register_admin_chat_routes
from web.backend.roles.admin.routes.office_hours_routes import register_office_hours_admin_routes
from web.backend.roles.admin.services.page_service import (
    build_admin_page_context,
    build_edit_student_page_context,
)
from web.backend.utils.session import (
    current_auth_login,
    current_auth_role,
)
from web.backend.roles.admin.services.academic_service import list_admin_academic_context
from web.backend.domains.announcements.service import list_announcements


def register_admin_page_routes(
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
        requested_panel = str(request.args.get("panel", "") or "").strip()
        requested_school = str(request.args.get("school", "") or "").strip()
        if requested_panel and str(admin_panel or "overview").strip().lower() == "overview":
            admin_panel = requested_panel
        if requested_school and str(admin_school or "all").strip().lower() == "all":
            admin_school = requested_school

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
        )
        academic_context = list_admin_academic_context()
        announcements = list_announcements()

        panel = page_context["panel"]
        school_filter = page_context["school_filter"]
        if current_auth_role() == "admin":
            session["admin_last_panel"] = panel
            session["admin_last_school"] = school_filter

        resolved_admin_mode = str(admin_mode or "").strip().lower()

        return render_react_page(
            "admin-home",
            {
                "authLogin": current_auth_login(),
                "authError": auth_error or (page_context["sync_errors"][0] if page_context["sync_errors"] else ""),
                "adminNotice": admin_notice or page_context["load_error"] or "",
                "adminPanel": panel,
                "adminMode": resolved_admin_mode,
                "adminSchool": school_filter,
                "adminStudents": page_context["admin_students"],
                "adminTeachers": page_context["admin_teachers"],
                "adminTeacherCandidates": page_context["admin_teacher_candidates"],
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
                "adminAnnouncements": announcements,
                "csrfToken": generate_csrf(),
            },
            title="MSI Admin Panel",
            description="Admin panel for school performance, teachers, students, and resources.",
            telegram=True,
        )

    def render_edit_student_page(student_row_id, auth_error="", admin_notice=""):
        context = build_edit_student_page_context(student_row_id)
        if not context:
            return None

        back_url = url_for("student.home", panel="students")
        return render_react_page(
            "admin-edit-student",
            {
                "authLogin": current_auth_login(),
                "authError": auth_error,
                "adminNotice": admin_notice,
                "student": context["student"],
                "teacherNameOptions": context["teacher_name_options"],
                "csrfToken": generate_csrf(),
                "saveUrl": url_for("admin.save_admin_student_profile", student_row_id=student_row_id),
                "changePasswordUrl": url_for("admin.admin_change_student_password_route", student_row_id=student_row_id),
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

    admin_routes = RouteGroup("admin", __name__)

    @admin_routes.before_request
    def ensure_admin_role():
        if current_auth_role() == "admin":
            return None
        requested_with = str(request.headers.get("X-Requested-With", "")).strip()
        if requested_with == "XMLHttpRequest":
            return jsonify({"ok": False, "message": "Admin authentication required."}), 401
        return redirect(url_for("student.home"))

    register_academic_admin_routes(
        admin_routes,
        render_admin_page=render_admin_page,
    )
    register_announcement_admin_routes(admin_routes)

    register_admin_routes(
        admin_routes,
        render_admin_page=render_admin_page,
        render_edit_student_page=render_edit_student_page,
        delete_uploaded_student_photo=delete_uploaded_student_photo,
    )
    register_admin_chat_routes(admin_routes)
    register_office_hours_admin_routes(admin_routes)
    app.include_router(admin_routes)
    return render_admin_page
