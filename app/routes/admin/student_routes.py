import os
import time

from flask import current_app, redirect, request, session, url_for
from werkzeug.utils import secure_filename

from app.routes.admin.services.auth_service import (
    assign_teacher_to_group,
    get_admin_student_profile,
    list_teachers,
    update_student_admin_profile,
)
from app.routes.admin.services.route_service import resolve_sheet_student_for_admin


def register_admin_student_routes(
    router,
    *,
    render_admin_page,
    render_edit_student_page,
    delete_uploaded_student_photo,
    load_dataset,
):
    @router.get("/admin/students/<int:student_row_id>")
    def admin_student_profile(student_row_id):
        admin_notice = request.args.get("notice", "").strip()
        rendered = render_edit_student_page(
            student_row_id,
            admin_notice=admin_notice,
        )
        if rendered is None:
            return (
                render_admin_page(
                    auth_error="Selected student was not found.",
                    admin_panel="students",
                ),
                404,
            )

        return rendered

    @router.get("/admin/students/<int:student_row_id>/dashboard")
    def admin_student_dashboard(student_row_id):
        requested_school = str(request.args.get("school", "")).strip().casefold()
        if not requested_school:
            requested_school = (
                str(session.get("admin_last_school", "all")).strip().casefold() or "all"
            )
        session["admin_last_panel"] = "students"
        session["admin_last_school"] = requested_school

        resolved, resolve_error, status_code = resolve_sheet_student_for_admin(
            student_row_id,
            get_admin_student_profile,
            load_dataset,
        )
        if resolve_error:
            return (
                render_admin_page(
                    auth_error=resolve_error,
                    admin_panel="students",
                ),
                status_code,
            )

        return redirect(
            url_for(
                "student.dashboard",
                student_id=int(resolved["student_id"]),
                subject=resolved.get("subject", ""),
                group=resolved.get("group", ""),
                school=resolved.get("school", ""),
                admin_return_panel="students",
                admin_return_school=requested_school,
            )
        )

    @router.post("/admin/students/<int:student_row_id>/profile")
    def save_admin_student_profile(student_row_id):
        current_profile = get_admin_student_profile(student_row_id, load_dataset)
        if not current_profile:
            return (
                render_admin_page(
                    auth_error="Selected student was not found.",
                    admin_panel="students",
                ),
                404,
            )

        teacher_name_raw = request.form.get("teacher_name")
        normalized_teacher_name = str(teacher_name_raw or "").strip()

        photo_url = request.form.get("photo_url", "").strip()
        previous_photo_url = str(current_profile.get("photo_url", "")).strip()
        remove_photo_requested = request.form.get("remove_photo", "0") == "1"
        if remove_photo_requested and previous_photo_url:
            delete_uploaded_student_photo(previous_photo_url)
            photo_url = ""

        uploaded_photo = request.files.get("photo_file")
        if uploaded_photo and uploaded_photo.filename:
            file_name = secure_filename(uploaded_photo.filename)
            _, extension = os.path.splitext(file_name)
            extension = extension.lower()
            allowed_extensions = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
            if extension not in allowed_extensions:
                rendered = render_edit_student_page(
                    student_row_id,
                    auth_error="Photo format is not supported. Use PNG, JPG, JPEG, WEBP, or GIF.",
                )
                if rendered is not None:
                    return rendered, 400
            else:
                static_root = current_app.static_folder or os.path.join(
                    current_app.root_path,
                    "web",
                    "static",
                )
                uploads_dir = os.path.join(
                    static_root,
                    "uploads",
                    "student_photos",
                )
                os.makedirs(uploads_dir, exist_ok=True)
                final_name = f"student_{student_row_id}_{int(time.time())}{extension}"
                final_path = os.path.join(uploads_dir, final_name)
                uploaded_photo.save(final_path)
                photo_url = url_for(
                    "static",
                    filename=f"uploads/student_photos/{final_name}",
                )
                if previous_photo_url:
                    delete_uploaded_student_photo(previous_photo_url)

        available_teacher_names = {
            str(row.get("full_name", "")).strip()
            for row in list_teachers()
            if str(row.get("full_name", "")).strip()
        }
        if (
            normalized_teacher_name
            and normalized_teacher_name != "__none__"
            and normalized_teacher_name not in available_teacher_names
        ):
            rendered = render_edit_student_page(
                student_row_id,
                auth_error="Selected teacher is not available in the database.",
            )
            if rendered is not None:
                return rendered, 400

        assigned_group = str(current_profile.get("group", "")).strip()
        teacher_to_assign = normalized_teacher_name
        if normalized_teacher_name == "__none__":
            teacher_to_assign = ""

        if assigned_group:
            assigned_ok = assign_teacher_to_group(assigned_group, teacher_to_assign)
            if not assigned_ok:
                rendered = render_edit_student_page(
                    student_row_id,
                    auth_error="Unable to update teacher assignment for this group.",
                )
                if rendered is not None:
                    return rendered, 400

        saved = update_student_admin_profile(
            student_row_id=student_row_id,
            photo_url=photo_url,
            profile_description=request.form.get("profile_description", "").strip(),
            class_name=str(current_profile.get("class_name", "")).strip(),
            school_name=str(current_profile.get("school_name", "")).strip() or "School 5",
            teacher_name="",
        )
        if not saved:
            # Clean up the newly uploaded photo so it doesn't become an orphan.
            if photo_url and photo_url != previous_photo_url:
                delete_uploaded_student_photo(photo_url)
            rendered = render_edit_student_page(
                student_row_id,
                auth_error="Unable to save student profile details.",
            )
            if rendered is not None:
                return rendered, 400
            return (
                render_admin_page(
                    auth_error="Unable to save student profile details.",
                    admin_panel="students",
                ),
                400,
            )

        return redirect(
            url_for(
                "admin.admin_student_profile",
                student_row_id=student_row_id,
                notice="Student profile updated.",
            )
        )
