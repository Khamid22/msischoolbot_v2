import os
import time

from itsdangerous import URLSafeTimedSerializer

from web.backend.utils.response_helpers import jsonify, redirect
from web.backend.utils.context import current_app, request, session
from web.backend.utils.session import url_for
from werkzeug.utils import secure_filename

from shared.identity.account_service import (
    admin_change_student_password,
    assign_teacher_to_group,
    get_admin_student_profile,
    list_students_for_admin,
    list_teachers,
    update_student_admin_profile,
)
from web.backend.roles.admin.routes.request_payload import request_payload
from web.backend.roles.admin.services.academic_service import (
    create_student_with_enrollment_from_payload,
)
from web.backend.roles.admin.services.page_service import invalidate_admin_page_context_cache
from web.backend.roles.admin.services.route_service import resolve_sheet_student_for_admin


STUDENT_DASHBOARD_TARGET_ENDPOINTS = {
    "dashboard": "student.dashboard",
    "resources": "student.student_resources",
    "chat": "student.chat_room",
    "rating": "student.rating_board",
    "aap": "student.aap_lessons",
    "ar": "student.ar_lessons",
    "office-hours": "student.student_office_hours",
    "office_hours": "student.student_office_hours",
}


def _parent_invite_serializer():
    secret = os.environ.get("APP_SECRET_KEY", os.environ.get("FLASK_SECRET_KEY", "")).strip()
    if not secret:
        raise RuntimeError("APP_SECRET_KEY is required to generate parent invite links.")
    return URLSafeTimedSerializer(secret_key=secret, salt="msi-parent-invite-v1")


def _request_public_base_url():
    proto = str(request.headers.get("x-forwarded-proto") or "").split(",")[0].strip()
    if not proto:
      proto = "https" if str(request.headers.get("x-forwarded-ssl", "")).lower() == "on" else "http"
    host = str(request.headers.get("x-forwarded-host") or request.host or "").split(",")[0].strip()
    return f"{proto}://{host}".rstrip("/") if host else ""


def register_admin_student_routes(
    router,
    *,
    render_admin_page,
    render_edit_student_page,
    delete_uploaded_student_photo,
):
    @router.get("/admin/api/students")
    def admin_students_api():
        school_filter = str(request.args.get("school", "all")).strip().casefold()
        if school_filter not in {"all", "school5", "sehriyo"}:
            school_filter = "all"
        students = list_students_for_admin(school_filter=school_filter)
        return jsonify({"students": students})

    @router.post("/admin/api/students")
    def admin_create_student_api():
        try:
            result = create_student_with_enrollment_from_payload(request_payload())
        except (TypeError, ValueError) as exc:
            return jsonify({"ok": False, "message": str(exc)}), 400
        invalidate_admin_page_context_cache()
        return jsonify({"ok": True, "student": result})

    @router.post("/admin/api/students/<int:student_row_id>/parent-invite")
    def admin_create_parent_invite(student_row_id):
        profile = get_admin_student_profile(student_row_id)
        if not profile:
            return jsonify({"ok": False, "message": "Selected student was not found."}), 404

        token = _parent_invite_serializer().dumps(
            {
                "student_row_id": int(student_row_id),
                "student_code": str(profile.get("student_code") or profile.get("student_id") or "").strip(),
                "student_name": str(profile.get("full_name") or "").strip(),
                "issued_by": int(session.get("admin_id", 0) or 0),
                "issued_at": int(time.time()),
            }
        )
        invite_path = f"/parent/link/{token}"
        base_url = _request_public_base_url()
        invite_url = f"{base_url}{invite_path}" if base_url else invite_path
        return jsonify({"ok": True, "invite_url": invite_url, "inviteUrl": invite_url})

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
        return _redirect_admin_student_dashboard(student_row_id, "dashboard")

    @router.get("/admin/students/<int:student_row_id>/dashboard/<target>")
    def admin_student_dashboard_target(student_row_id, target):
        return _redirect_admin_student_dashboard(student_row_id, target)

    def _redirect_admin_student_dashboard(student_row_id, target):
        requested_school = str(request.args.get("school", "")).strip().casefold()
        embed_mode = str(request.args.get("embed", "")).strip() or "admin"
        if not requested_school:
            requested_school = (
                str(session.get("admin_last_school", "all")).strip().casefold() or "all"
            )
        session["admin_last_panel"] = "students"
        session["admin_last_school"] = requested_school
        normalized_target = str(target or "dashboard").strip().lower()
        endpoint = STUDENT_DASHBOARD_TARGET_ENDPOINTS.get(normalized_target)
        if not endpoint:
            return (
                render_admin_page(
                    auth_error="Selected student page is not available.",
                    admin_panel="students",
                ),
                404,
            )

        resolved, resolve_error, status_code = resolve_sheet_student_for_admin(
            student_row_id,
            get_admin_student_profile,
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
                endpoint,
                student_id=int(resolved["student_id"]),
                subject=resolved.get("subject", ""),
                group=resolved.get("group", ""),
                school=resolved.get("school", ""),
                admin_return_panel="students",
                admin_return_school=requested_school,
                embed=embed_mode,
            )
        )

    @router.post("/admin/students/<int:student_row_id>/profile")
    def save_admin_student_profile(student_row_id):
        current_profile = get_admin_student_profile(student_row_id)
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
                if os.path.getsize(final_path) > 10 * 1024 * 1024:  # 10 MB cap
                    try:
                        os.remove(final_path)
                    except OSError:
                        pass
                    rendered = render_edit_student_page(
                        student_row_id,
                        auth_error="Photo is too large. Maximum file size is 10 MB.",
                    )
                    if rendered is not None:
                        return rendered, 413
                else:
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

    @router.post("/admin/students/<int:student_row_id>/password")
    def admin_change_student_password_route(student_row_id):
        new_password = request.form.get("new_password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        if new_password != confirm_password:
            rendered = render_edit_student_page(
                student_row_id,
                auth_error="Passwords do not match.",
            )
            if rendered is not None:
                return rendered, 400
            return (
                render_admin_page(
                    auth_error="Passwords do not match.",
                    admin_panel="students",
                ),
                400,
            )

        changed, change_error = admin_change_student_password(student_row_id, new_password)
        if not changed:
            rendered = render_edit_student_page(
                student_row_id,
                auth_error=change_error or "Unable to change password.",
            )
            if rendered is not None:
                return rendered, 400
            return (
                render_admin_page(
                    auth_error=change_error or "Unable to change password.",
                    admin_panel="students",
                ),
                400,
            )

        return redirect(
            url_for(
                "admin.admin_student_profile",
                student_row_id=student_row_id,
                notice="Password changed successfully.",
            )
        )
