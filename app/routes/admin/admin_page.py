import os

from flask import Blueprint, redirect, render_template, session, url_for

from app.routes.admin.admins import register_admin_routes
from app.routes.admin.services.page_service import (
    build_admin_page_context,
    build_edit_student_page_context,
)
from app.routes.admin.services.session_state_service import (
    current_auth_login,
    current_auth_role,
)


def register_admin_page_routes(
    app,
    *,
    load_dataset,
):
    def should_force_refresh():
        return False

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
        admin_selected_student=None,
        admin_teacher_edit=None,
        admin_school="all",
    ):
        _ = admin_selected_student  # Kept for backward compatibility.
        force_refresh = should_force_refresh()
        page_context = build_admin_page_context(
            admin_panel=admin_panel,
            admin_school=admin_school,
            admin_teacher_edit=admin_teacher_edit,
            load_dataset=load_dataset,
            force_refresh=force_refresh,
        )

        panel = page_context["panel"]
        school_filter = page_context["school_filter"]
        if current_auth_role() == "admin":
            session["admin_last_panel"] = panel
            session["admin_last_school"] = school_filter

        return render_template(
            "admin/home.html",
            error="",
            auth_login=current_auth_login(),
            auth_error=auth_error or (page_context["sync_errors"][0] if page_context["sync_errors"] else ""),
            admin_students=page_context["admin_students"],
            admin_panel=panel,
            admin_teachers=page_context["admin_teachers"],
            admin_teacher_options=page_context["admin_teacher_options"],
            admin_group_options=page_context["admin_group_options"],
            admin_teacher_edit=page_context["admin_teacher_edit"],
            admin_teacher_edit_school=page_context["admin_teacher_edit_school"],
            admin_school=school_filter,
            admin_school_options=page_context["admin_school_options"],
            admin_notice=admin_notice or page_context["load_error"] or "",
            admin_quick_stats=page_context["admin_quick_stats"],
            admin_school_info=page_context["admin_school_info"],
            admin_subject_info=page_context["admin_subject_info"],
            admin_group_zones=page_context["admin_group_zones"],
            admin_resource_types=page_context["admin_resource_types"],
            admin_resource_active_types=page_context["admin_resource_active_types"],
            admin_resources=page_context["admin_resources"],
            admin_resource_subject_options=page_context["admin_resource_subject_options"],
            admin_resource_upload_enabled=page_context["admin_resource_upload_enabled"],
        )

    def render_edit_student_page(student_row_id, auth_error="", admin_notice=""):
        context = build_edit_student_page_context(student_row_id, load_dataset)
        if not context:
            return None

        return render_template(
            "admin/edit_student_profile.html",
            auth_login=current_auth_login(),
            auth_error=auth_error,
            admin_notice=admin_notice,
            student=context["student"],
            teacher_name_options=context["teacher_name_options"],
        )

    admin_blueprint = Blueprint("admin", __name__)

    @admin_blueprint.before_request
    def ensure_admin_role():
        if current_auth_role() == "admin":
            return None
        return redirect(url_for("student.home"))

    register_admin_routes(
        admin_blueprint,
        render_admin_page=render_admin_page,
        render_edit_student_page=render_edit_student_page,
        delete_uploaded_student_photo=delete_uploaded_student_photo,
        load_dataset=load_dataset,
    )
    app.register_blueprint(admin_blueprint)
    return render_admin_page
