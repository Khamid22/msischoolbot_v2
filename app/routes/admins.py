import os
import time

from flask import redirect, request, session, url_for
from werkzeug.utils import secure_filename


def register_admin_routes(
    app,
    *,
    current_auth_role,
    render_admin_page,
    render_edit_student_page,
    delete_uploaded_student_photo,
    load_dataset,
    get_admin_student_profile,
    assign_teacher_to_group,
    update_student_admin_profile,
    list_teachers,
    get_teacher_by_id,
    update_teacher_by_id,
    upsert_teacher,
    delete_teacher_by_id,
):
    def _school_code_from_name(school_name):
        normalized = str(school_name or "").strip().casefold()
        if normalized == "sehriyo":
            return "sehriyo"
        if normalized in {"school 5", "school5"}:
            return "school5"
        return ""

    def _normalize_name(value):
        return " ".join(str(value or "").strip().casefold().split())

    def _resolve_sheet_student_for_admin(student_row_id):
        student_profile = get_admin_student_profile(student_row_id, load_dataset)
        if not student_profile:
            return None, "Selected student was not found.", 404

        school_code = _school_code_from_name(student_profile.get("school_name", ""))
        if school_code:
            try:
                dataset, load_error = load_dataset(school_code=school_code)
            except TypeError:
                dataset, load_error = load_dataset()
        else:
            dataset, load_error = load_dataset()
        if load_error or not dataset:
            return None, load_error or "Unable to load Google Sheets data.", 503

        students = dataset.get("students", [])
        if not isinstance(students, list):
            return None, "Students dataset is invalid.", 503

        target_name_norm = _normalize_name(student_profile.get("full_name", ""))
        preferred_group = str(student_profile.get("group", "")).strip()
        candidates = []

        for student in students:
            if not isinstance(student, dict):
                continue

            if _normalize_name(student.get("fullName", "")) != target_name_norm:
                continue

            sheet_student_id = student.get("id")
            if not isinstance(sheet_student_id, int) or sheet_student_id <= 0:
                continue

            subject_name = str(student.get("subject", "")).strip()
            group_name = str(student.get("group", "")).strip()
            candidates.append(
                {
                    "student_id": int(sheet_student_id),
                    "subject": subject_name,
                    "group": group_name,
                    "school": school_code,
                    "group_match": bool(preferred_group and group_name == preferred_group),
                }
            )

        if not candidates:
            return None, "No dashboard data found for this student.", 404

        candidates.sort(
            key=lambda item: (
                0 if item.get("group_match") else 1,
                str(item.get("subject", "")).casefold(),
                str(item.get("group", "")).casefold(),
                int(item.get("student_id", 0)),
            )
        )

        return candidates[0], "", 200

    @app.get("/admin/students/<int:student_row_id>")
    def admin_student_profile(student_row_id):
        if current_auth_role() != "admin":
            return redirect(url_for("home"))

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

    @app.get("/admin/students/<int:student_row_id>/dashboard")
    def admin_student_dashboard(student_row_id):
        if current_auth_role() != "admin":
            return redirect(url_for("home"))

        requested_school = str(request.args.get("school", "")).strip().casefold()
        if not requested_school:
            requested_school = str(session.get("admin_last_school", "all")).strip().casefold() or "all"
        session["admin_last_panel"] = "students"
        session["admin_last_school"] = requested_school

        resolved, resolve_error, status_code = _resolve_sheet_student_for_admin(student_row_id)
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
                "dashboard",
                student_id=int(resolved["student_id"]),
                subject=resolved.get("subject", ""),
                group=resolved.get("group", ""),
                school=resolved.get("school", ""),
                admin_return_panel="students",
                admin_return_school=requested_school,
            )
        )

    @app.post("/admin/students/<int:student_row_id>/profile")
    def save_admin_student_profile(student_row_id):
        if current_auth_role() != "admin":
            return redirect(url_for("home"))

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
                static_root = app.static_folder or os.path.join(app.root_path, "web", "static")
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
                "admin_student_profile",
                student_row_id=student_row_id,
                notice="Student profile updated.",
            )
        )

    @app.post("/admin/teachers/add")
    def add_teacher():
        if current_auth_role() != "admin":
            return redirect(url_for("home"))

        edit_teacher_id_raw = request.form.get("teacher_edit_id", "").strip()
        edit_teacher_id = 0
        if edit_teacher_id_raw:
            try:
                edit_teacher_id = int(edit_teacher_id_raw)
            except ValueError:
                edit_teacher_id = 0

        mode = str(request.form.get("teacher_mode", "select")).strip().lower()
        assigned_group = request.form.get("teacher_assigned_group", "").strip()
        if not assigned_group:
            selected_teacher_edit = get_teacher_by_id(edit_teacher_id) if edit_teacher_id > 0 else None
            return (
                render_admin_page(
                    auth_error="Please select a group for teacher assignment.",
                    admin_panel="teachers",
                    admin_teacher_edit=selected_teacher_edit,
                ),
                400,
            )

        if mode == "add":
            candidate_full_name = request.form.get("teacher_full_name", "").strip()
            candidate_pay_rate = request.form.get("teacher_pay_rate", "").strip()
        else:
            selected_teacher_name = request.form.get("teacher_selected_name", "").strip()
            teacher_rows = list_teachers()
            selected_teacher = next(
                (
                    row
                    for row in teacher_rows
                    if str(row.get("full_name", "")).strip().casefold()
                    == selected_teacher_name.casefold()
                ),
                None,
            )
            if not selected_teacher:
                selected_teacher_edit = get_teacher_by_id(edit_teacher_id) if edit_teacher_id > 0 else None
                return (
                    render_admin_page(
                        auth_error="Please select an existing teacher.",
                        admin_panel="teachers",
                        admin_teacher_edit=selected_teacher_edit,
                    ),
                    400,
                )
            candidate_full_name = str(selected_teacher.get("full_name", "")).strip()
            candidate_pay_rate = float(selected_teacher.get("pay_rate", 0))

        if edit_teacher_id > 0:
            created, update_error = update_teacher_by_id(
                teacher_id=edit_teacher_id,
                full_name=candidate_full_name,
                pay_rate=candidate_pay_rate,
                assigned_group=assigned_group,
            )
            if not created:
                selected_teacher_edit = get_teacher_by_id(edit_teacher_id)
                return (
                    render_admin_page(
                        auth_error=update_error or "Unable to update teacher.",
                        admin_panel="teachers",
                        admin_teacher_edit=selected_teacher_edit,
                    ),
                    400,
                )
        else:
            created = upsert_teacher(
                full_name=candidate_full_name,
                pay_rate=candidate_pay_rate,
                assigned_group=assigned_group,
            )
            if not created:
                return (
                    render_admin_page(
                        auth_error="Unable to save teacher. Check full name, pay rate, and group.",
                        admin_panel="teachers",
                    ),
                    400,
                )

        return render_admin_page(
            admin_notice="Teacher changes saved.",
            admin_panel="teachers",
        )

    @app.post("/admin/teachers/<int:teacher_id>/delete")
    def delete_teacher(teacher_id):
        if current_auth_role() != "admin":
            return redirect(url_for("home"))

        deleted = delete_teacher_by_id(teacher_id)
        if not deleted:
            return (
                render_admin_page(
                    auth_error="Unable to delete teacher.",
                    admin_panel="teachers",
                ),
                400,
            )

        return render_admin_page(
            admin_notice="Teacher deleted.",
            admin_panel="teachers",
        )
