import os
import time

from flask import jsonify, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename

try:
    from ..auth_store import (
        assign_teacher_to_group,
        change_student_password,
        delete_teacher_by_id,
        detect_login_role,
        get_admin_student_profile,
        get_bot_users_count,
        get_student_by_telegram_user_id,
        get_teacher_by_id,
        init_storage,
        link_student_telegram_user,
        list_students_for_admin,
        list_teachers,
        unlink_student_telegram_user,
        sync_students_if_needed,
        update_teacher_by_id,
        update_student_admin_profile,
        upsert_teacher,
        verify_admin_credentials,
        verify_student_credentials,
    )
except ImportError:
    from auth_store import (
        assign_teacher_to_group,
        change_student_password,
        delete_teacher_by_id,
        detect_login_role,
        get_admin_student_profile,
        get_bot_users_count,
        get_student_by_telegram_user_id,
        get_teacher_by_id,
        init_storage,
        link_student_telegram_user,
        list_students_for_admin,
        list_teachers,
        unlink_student_telegram_user,
        sync_students_if_needed,
        update_teacher_by_id,
        update_student_admin_profile,
        upsert_teacher,
        verify_admin_credentials,
        verify_student_credentials,
    )


def register_home_routes(
    app,
    *,
    load_dataset,
    seed_group_cache_from_dataset,
    build_students_by_subject_group,
    empty_form_data,
    is_full_form,
    get_group_cache_entry,
    search_student,
):
    init_storage()

    def _current_auth_role():
        role = str(session.get("auth_role", "")).strip().lower()
        if role in {"admin", "student"}:
            return role
        return ""

    def _current_auth_login():
        return str(session.get("auth_login", "")).strip()

    def _current_student_sheet_id():
        raw_value = session.get("student_sheet_id")
        try:
            return int(raw_value)
        except (TypeError, ValueError):
            return None

    def _current_student_db_id():
        raw_value = session.get("student_db_id")
        try:
            return int(raw_value)
        except (TypeError, ValueError):
            return None

    def _parse_telegram_user_id(raw_value):
        try:
            parsed = int(str(raw_value).strip())
        except (TypeError, ValueError):
            return None
        if parsed <= 0:
            return None
        return parsed

    def _set_admin_session(admin):
        session.clear()
        session["auth_role"] = "admin"
        session["auth_login"] = str(admin.get("login", "")).strip()
        session["admin_id"] = int(admin["id"])
        session["admin_is_owner"] = bool(admin.get("is_owner"))
        session.permanent = True

    def _set_student_session(student, telegram_user_id):
        if not isinstance(student, dict):
            return False
        try:
            student_db_id = int(student["id"])
            sheet_student_id = int(student["sheet_student_id"])
        except (KeyError, TypeError, ValueError):
            return False

        if student_db_id <= 0 or sheet_student_id <= 0:
            return False

        session.clear()
        session["auth_role"] = "student"
        session["auth_login"] = str(student.get("student_id", "")).strip()
        session["student_db_id"] = student_db_id
        session["student_id"] = str(student.get("student_id", "")).strip()
        session["student_sheet_id"] = sheet_student_id
        session["student_full_name"] = str(student.get("full_name", "")).strip()
        session["telegram_user_id"] = telegram_user_id
        session.permanent = True
        return True

    def _try_auto_login_student_by_telegram(telegram_user_id):
        if not isinstance(telegram_user_id, int) or telegram_user_id <= 0:
            return False

        student = get_student_by_telegram_user_id(telegram_user_id)
        if not student:
            return False
        return _set_student_session(student, telegram_user_id)

    def _build_dashboard_url(student_sheet_id, subject="", group="", **extra_params):
        route_params = {
            "student_id": int(student_sheet_id),
        }
        normalized_subject = str(subject or "").strip()
        normalized_group = str(group or "").strip()
        if normalized_subject:
            route_params["subject"] = normalized_subject
        if normalized_group:
            route_params["group"] = normalized_group
        for key, value in extra_params.items():
            if str(value or "").strip():
                route_params[key] = str(value).strip()
        return url_for("dashboard", **route_params)

    def _delete_uploaded_student_photo(photo_url):
        raw_url = str(photo_url or "").strip()
        if not raw_url:
            return
        expected_prefix = "/static/uploads/student_photos/"
        if not raw_url.startswith(expected_prefix):
            return
        file_name = os.path.basename(raw_url)
        if not file_name:
            return
        uploads_dir = os.path.join(app.root_path, "static", "uploads", "student_photos")
        candidate_path = os.path.join(uploads_dir, file_name)
        if os.path.isfile(candidate_path):
            try:
                os.remove(candidate_path)
            except OSError:
                return

    def _render_login_page(auth_error="", auth_login_input=""):
        return render_template(
            "home.html",
            groups=[],
            groups_by_subject={},
            subjects=[],
            students_by_subject_group={},
            error="",
            form_data=empty_form_data(),
            auth_role="",
            auth_login="",
            auth_error=auth_error,
            auth_login_input=auth_login_input,
            bot_users_count=0,
            admin_students=[],
            admin_panel="students",
            admin_teachers=[],
            admin_teacher_name_options=[],
            admin_groups=[],
            admin_selected_student=None,
            admin_teacher_edit=None,
            admin_notice="",
        )

    def _render_admin_page(
        auth_error="",
        admin_notice="",
        admin_panel="students",
        admin_selected_student=None,
        admin_teacher_edit=None,
    ):
        sync_result = sync_students_if_needed(load_dataset)
        sync_error = str(sync_result.get("error", "")).strip()
        dataset, load_error = load_dataset()
        groups = dataset["groups"] if dataset else []
        panel = str(admin_panel or "students").strip().lower()
        if panel not in {"students", "teachers"}:
            panel = "students"

        admin_teachers = list_teachers()
        admin_teacher_name_options = sorted(
            {
                str(row.get("full_name", "")).strip()
                for row in admin_teachers
                if str(row.get("full_name", "")).strip()
            },
            key=lambda value: value.casefold(),
        )

        return render_template(
            "home.html",
            groups=[],
            groups_by_subject={},
            subjects=[],
            students_by_subject_group={},
            error="",
            form_data=empty_form_data(),
            auth_role="admin",
            auth_login=_current_auth_login(),
            auth_error=auth_error or sync_error,
            auth_login_input="",
            bot_users_count=get_bot_users_count(),
            admin_students=list_students_for_admin(),
            admin_panel=panel,
            admin_teachers=admin_teachers,
            admin_teacher_name_options=admin_teacher_name_options,
            admin_groups=groups,
            admin_selected_student=admin_selected_student,
            admin_teacher_edit=admin_teacher_edit,
            admin_notice=admin_notice or load_error or "",
        )

    def _render_edit_student_page(student_row_id, auth_error="", admin_notice=""):
        selected_student = get_admin_student_profile(student_row_id, load_dataset)
        if not selected_student:
            return None

        teacher_rows = list_teachers()
        teacher_name_options = sorted(
            {
                str(row.get("full_name", "")).strip()
                for row in teacher_rows
                if str(row.get("full_name", "")).strip()
            },
            key=lambda value: value.casefold(),
        )

        return render_template(
            "edit_student_profile.html",
            auth_login=_current_auth_login(),
            auth_error=auth_error,
            admin_notice=admin_notice,
            student=selected_student,
            teacher_name_options=teacher_name_options,
        )

    def _render_student_panel(form_data, panel_error=""):
        dataset, load_error = load_dataset()
        groups = dataset["groups"] if dataset else []
        groups_by_subject = dataset["groups_by_subject"] if dataset else {}
        subjects = dataset["subjects"] if dataset else []

        if dataset:
            seed_group_cache_from_dataset(dataset)

        students_by_subject_group = (
            build_students_by_subject_group(dataset["students"]) if dataset else {}
        )

        return render_template(
            "home.html",
            groups=groups,
            groups_by_subject=groups_by_subject,
            subjects=subjects,
            students_by_subject_group=students_by_subject_group,
            error=panel_error or load_error or "",
            form_data=form_data,
            auth_role="student",
            auth_login=_current_auth_login(),
            auth_error="",
            auth_login_input="",
            bot_users_count=0,
            admin_students=[],
            admin_panel="students",
            admin_teachers=[],
            admin_teacher_name_options=[],
            admin_groups=[],
            admin_selected_student=None,
            admin_teacher_edit=None,
            admin_notice="",
        )

    # Home page now works as auth entry + role-based panel.
    @app.get("/")
    def home():
        role = _current_auth_role()

        if role == "admin":
            panel = request.args.get("panel", "students")
            edit_teacher_id = request.args.get("edit_teacher_id", "").strip()
            selected_teacher_edit = None
            if panel == "teachers" and edit_teacher_id:
                try:
                    parsed_teacher_id = int(edit_teacher_id)
                except ValueError:
                    parsed_teacher_id = 0
                if parsed_teacher_id > 0:
                    selected_teacher_edit = get_teacher_by_id(parsed_teacher_id)
            return _render_admin_page(
                admin_panel=panel,
                admin_teacher_edit=selected_teacher_edit,
            )

        if role == "student":
            own_sheet_student_id = _current_student_sheet_id()
            if own_sheet_student_id is None:
                session.clear()
                return _render_login_page(
                    auth_error="Student session is invalid. Please login again.",
                ), 401
            return redirect(url_for("dashboard", student_id=own_sheet_student_id))

        auto_login_allowed = request.args.get("logged_out", "").strip() != "1"
        telegram_user_id = _parse_telegram_user_id(request.args.get("tg_user_id"))
        if (
            auto_login_allowed
            and telegram_user_id
            and _try_auto_login_student_by_telegram(telegram_user_id)
        ):
            own_sheet_student_id = _current_student_sheet_id()
            if own_sheet_student_id is not None:
                return redirect(
                    _build_dashboard_url(
                        own_sheet_student_id,
                    )
                )

        return _render_login_page()

    @app.post("/login")
    def login():
        login_value = request.form.get("login", "").strip()
        password_value = request.form.get("password", "").strip()

        if not login_value or not password_value:
            return _render_login_page(
                auth_error="Please enter both login and password.",
                auth_login_input=login_value,
            ), 400

        role_hint = detect_login_role(login_value)
        if not role_hint:
            return _render_login_page(
                auth_error="Login must start with Staff##### or MSI#####.",
                auth_login_input=login_value,
            ), 400

        if role_hint == "admin":
            admin = verify_admin_credentials(login_value, password_value)
            if not admin:
                return _render_login_page(
                    auth_error="Invalid admin credentials.",
                    auth_login_input=login_value,
                ), 401

            _set_admin_session(admin)
            return redirect(url_for("home"))

        sync_result = sync_students_if_needed(load_dataset)
        sync_error = str(sync_result.get("error", "")).strip()
        if sync_error:
            return _render_login_page(
                auth_error=sync_error,
                auth_login_input=login_value,
            ), 503

        student = verify_student_credentials(login_value, password_value)
        if not student:
            return _render_login_page(
                auth_error="Invalid student credentials.",
                auth_login_input=login_value,
            ), 401

        telegram_user_id = _parse_telegram_user_id(
            request.form.get("telegram_user_id")
        )
        if telegram_user_id is None:
            return _render_login_page(
                auth_error="Student authentication is available only through the Telegram mini app.",
                auth_login_input=login_value,
            ), 401

        linked = link_student_telegram_user(
            int(student["id"]),
            telegram_user_id,
        )
        if not linked:
            return _render_login_page(
                auth_error="Unable to link Telegram account. Please try again from the mini app.",
                auth_login_input=login_value,
            ), 500

        if not _set_student_session(student, telegram_user_id):
            return _render_login_page(
                auth_error="Unable to initialize student session.",
                auth_login_input=login_value,
            ), 500
        return redirect(
            url_for(
                "dashboard",
                student_id=student["sheet_student_id"],
            )
        )

    @app.post("/profile/password")
    def profile_change_password():
        if _current_auth_role() != "student":
            return redirect(url_for("home"))

        student_db_id = _current_student_db_id()
        student_sheet_id = _current_student_sheet_id()
        if student_db_id is None or student_sheet_id is None:
            session.clear()
            return redirect(url_for("home"))

        subject = request.form.get("subject", "").strip()
        group = request.form.get("group", "").strip()

        current_password_value = request.form.get("current_password", "")
        new_password_value = request.form.get("new_password", "")
        confirm_password_value = request.form.get("confirm_password", "")

        if new_password_value != confirm_password_value:
            return redirect(
                _build_dashboard_url(
                    student_sheet_id,
                    subject=subject,
                    group=group,
                    profile_error="New password and confirmation do not match.",
                )
            )

        updated, update_error = change_student_password(
            student_db_id,
            current_password=current_password_value,
            new_password=new_password_value,
        )
        if not updated:
            return redirect(
                _build_dashboard_url(
                    student_sheet_id,
                    subject=subject,
                    group=group,
                    profile_error=update_error or "Unable to change password.",
                )
            )

        return redirect(
            _build_dashboard_url(
                student_sheet_id,
                subject=subject,
                group=group,
                profile_notice="Password changed successfully.",
            )
        )

    @app.post("/logout")
    def logout():
        if _current_auth_role() == "student":
            student_db_id = _current_student_db_id()
            if student_db_id is not None:
                unlink_student_telegram_user(student_db_id)
        session.clear()
        return redirect(url_for("home", logged_out=1))

    @app.get("/admin/students/<int:student_row_id>")
    def admin_student_profile(student_row_id):
        if _current_auth_role() != "admin":
            return redirect(url_for("home"))

        admin_notice = request.args.get("notice", "").strip()
        rendered = _render_edit_student_page(
            student_row_id,
            admin_notice=admin_notice,
        )
        if rendered is None:
            return (
                _render_admin_page(
                    auth_error="Selected student was not found.",
                    admin_panel="students",
                ),
                404,
            )

        return rendered

    @app.post("/admin/students/<int:student_row_id>/profile")
    def save_admin_student_profile(student_row_id):
        if _current_auth_role() != "admin":
            return redirect(url_for("home"))

        current_profile = get_admin_student_profile(student_row_id, load_dataset)
        if not current_profile:
            return (
                _render_admin_page(
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
            _delete_uploaded_student_photo(previous_photo_url)
            photo_url = ""

        uploaded_photo = request.files.get("photo_file")
        if uploaded_photo and uploaded_photo.filename:
            file_name = secure_filename(uploaded_photo.filename)
            _, extension = os.path.splitext(file_name)
            extension = extension.lower()
            allowed_extensions = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
            if extension not in allowed_extensions:
                rendered = _render_edit_student_page(
                    student_row_id,
                    auth_error="Photo format is not supported. Use PNG, JPG, JPEG, WEBP, or GIF.",
                )
                if rendered is not None:
                    return rendered, 400
            else:
                uploads_dir = os.path.join(
                    app.root_path,
                    "static",
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
                    _delete_uploaded_student_photo(previous_photo_url)

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
            rendered = _render_edit_student_page(
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
                rendered = _render_edit_student_page(
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
            school_name="School 5",
            teacher_name="",
        )
        if not saved:
            rendered = _render_edit_student_page(
                student_row_id,
                auth_error="Unable to save student profile details.",
            )
            if rendered is not None:
                return rendered, 400
            return (
                _render_admin_page(
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
        if _current_auth_role() != "admin":
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
                _render_admin_page(
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
                    _render_admin_page(
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
                    _render_admin_page(
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
                    _render_admin_page(
                        auth_error="Unable to save teacher. Check full name, pay rate, and group.",
                        admin_panel="teachers",
                    ),
                    400,
                )

        return _render_admin_page(
            admin_notice="Teacher changes saved.",
            admin_panel="teachers",
        )

    @app.post("/admin/teachers/<int:teacher_id>/delete")
    def delete_teacher(teacher_id):
        if _current_auth_role() != "admin":
            return redirect(url_for("home"))

        deleted = delete_teacher_by_id(teacher_id)
        if not deleted:
            return (
                _render_admin_page(
                    auth_error="Unable to delete teacher.",
                    admin_panel="teachers",
                ),
                400,
            )

        return _render_admin_page(
            admin_notice="Teacher deleted.",
            admin_panel="teachers",
        )

    @app.post("/search")
    def search_student_form():
        # Read selected student/group/subject from the submitted form.
        if _current_auth_role() != "student":
            return redirect(url_for("home"))

        form_data = {
            "student_id": request.form.get("student_id", "").strip(),
            "group": request.form.get("group", "").strip(),
            "subject": request.form.get("subject", "").strip(),
        }

        if not is_full_form(form_data):
            return _render_student_panel(
                form_data=form_data,
                panel_error="Please fill all fields.",
            ), 400

        try:
            requested_student_id = int(form_data["student_id"])
        except ValueError:
            return _render_student_panel(
                form_data=form_data,
                panel_error="Please choose a valid student from the list.",
            ), 400

        group_cache_entry, cache_error = get_group_cache_entry(
            form_data["subject"],
            form_data["group"],
        )
        if group_cache_entry and requested_student_id in group_cache_entry.get(
            "dashboards_by_id", {}
        ):
            return redirect(
                url_for(
                    "dashboard",
                    student_id=requested_student_id,
                    subject=form_data["subject"],
                    group=form_data["group"],
                )
            )

        dataset, load_error = load_dataset()
        if load_error or not dataset:
            return _render_student_panel(
                form_data=form_data,
                panel_error=load_error
                or cache_error
                or "Unable to load Google Sheets data.",
            ), 503

        return _render_student_panel(
            form_data=form_data,
            panel_error="Student not found. Please check your details.",
        ), 404

    @app.get("/api/metadata")
    def api_metadata():
        # Frontend metadata used to build select options quickly.
        dataset, load_error = load_dataset()
        if load_error or not dataset:
            return jsonify(
                {"message": load_error or "Unable to load Google Sheets data."}
            ), 503

        return jsonify(
            {
                "groups": dataset["groups"],
                "groupsBySubject": dataset["groups_by_subject"],
                "studentsBySubjectGroup": build_students_by_subject_group(
                    dataset["students"]
                ),
                "subjects": dataset["subjects"],
            }
        )

    @app.get("/api/students/search")
    def api_search_student():
        # API search endpoint for frontend autocomplete and validation.
        surname = request.args.get("surname", "").strip()
        name = request.args.get("name", "").strip()
        group = request.args.get("group", "").strip()
        subject = request.args.get("subject", "").strip()

        if not all([surname, name, group, subject]):
            return jsonify({"message": "All fields are required."}), 400

        dataset, load_error = load_dataset()
        if load_error or not dataset:
            return jsonify(
                {"message": load_error or "Unable to load Google Sheets data."}
            ), 503

        student = search_student(
            dataset["students"],
            surname=surname,
            name=name,
            group=group,
            subject=subject,
        )
        if not student:
            return jsonify({"message": "Student not found"}), 404

        return jsonify(student)
