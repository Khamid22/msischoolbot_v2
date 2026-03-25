from flask import jsonify, redirect, request, session, url_for


def register_student_routes(
    app,
    *,
    current_auth_role,
    current_student_sheet_id,
    current_student_db_id,
    parse_telegram_user_id,
    set_admin_session,
    set_student_session,
    try_auto_login_student_by_telegram,
    build_dashboard_url,
    render_login_page,
    render_admin_page,
    get_teacher_by_id,
    detect_login_role,
    verify_admin_credentials,
    verify_student_credentials,
    sync_students_if_needed,
    load_dataset,
    link_student_telegram_user,
    change_student_password,
    unlink_student_telegram_user,
    is_full_form,
    render_student_panel,
    get_group_cache_entry,
    build_students_by_subject_group,
    search_student,
):
    def _normalize_school_code(value):
        normalized = str(value or "").strip().casefold()
        if normalized in {"school_5", "school-5", "school 5", "school5"}:
            return "school5"
        if normalized in {"sehriyo", "sehriyo school"}:
            return "sehriyo"
        return normalized

    def _current_student_school_code():
        return _normalize_school_code(session.get("student_school_code", ""))

    @app.get("/")
    def home():
        role = current_auth_role()

        if role == "admin":
            panel_arg = str(request.args.get("panel", "")).strip().lower()
            school_arg = str(request.args.get("school", "")).strip().lower()
            saved_panel = str(session.get("admin_last_panel", "overview")).strip().lower()
            saved_school = str(session.get("admin_last_school", "all")).strip().lower()

            panel = panel_arg or saved_panel or "overview"
            school_filter = school_arg or saved_school or "all"
            edit_teacher_id = request.args.get("edit_teacher_id", "").strip()
            selected_teacher_edit = None
            if panel == "teachers" and edit_teacher_id:
                try:
                    parsed_teacher_id = int(edit_teacher_id)
                except ValueError:
                    parsed_teacher_id = 0
                if parsed_teacher_id > 0:
                    selected_teacher_edit = get_teacher_by_id(parsed_teacher_id)
            return render_admin_page(
                admin_panel=panel,
                admin_teacher_edit=selected_teacher_edit,
                admin_school=school_filter,
            )

        if role == "student":
            own_sheet_student_id = current_student_sheet_id()
            if own_sheet_student_id is None:
                session.clear()
                return render_login_page(
                    auth_error="Student session is invalid. Please login again.",
                ), 401
            return redirect(build_dashboard_url(own_sheet_student_id))

        auto_login_allowed = request.args.get("logged_out", "").strip() != "1"
        telegram_user_id = parse_telegram_user_id(request.args.get("tg_user_id"))
        if (
            auto_login_allowed
            and telegram_user_id
            and try_auto_login_student_by_telegram(telegram_user_id)
        ):
            own_sheet_student_id = current_student_sheet_id()
            if own_sheet_student_id is not None:
                return redirect(
                    build_dashboard_url(
                        own_sheet_student_id,
                    )
                )

        return render_login_page()

    @app.post("/login")
    def login():
        login_value = request.form.get("login", "").strip()
        password_value = request.form.get("password", "").strip()

        if not login_value or not password_value:
            return render_login_page(
                auth_error="Please enter both login and password.",
                auth_login_input=login_value,
            ), 400

        role_hint = detect_login_role(login_value)
        if not role_hint:
            return render_login_page(
                auth_error="Login must start with Staff#####, MSI#####, or MSIS#####.",
                auth_login_input=login_value,
            ), 400

        if role_hint == "admin":
            admin = verify_admin_credentials(login_value, password_value)
            if not admin:
                return render_login_page(
                    auth_error="Invalid admin credentials.",
                    auth_login_input=login_value,
                ), 401

            set_admin_session(admin)
            return redirect(url_for("home"))

        normalized_login = login_value.strip().casefold()
        school_code = "sehriyo" if normalized_login.startswith("msis") else "school5"
        sync_result = sync_students_if_needed(
            load_dataset,
            school_code=school_code,
        )
        sync_error = str(sync_result.get("error", "")).strip()
        if sync_error:
            return render_login_page(
                auth_error=sync_error,
                auth_login_input=login_value,
            ), 503

        student = verify_student_credentials(login_value, password_value)
        if not student:
            return render_login_page(
                auth_error="Invalid student credentials.",
                auth_login_input=login_value,
            ), 401

        telegram_user_id = parse_telegram_user_id(
            request.form.get("telegram_user_id")
        )
        if telegram_user_id is None:
            return render_login_page(
                auth_error="Student authentication is available only through the Telegram mini app.",
                auth_login_input=login_value,
            ), 401

        linked = link_student_telegram_user(
            int(student["id"]),
            telegram_user_id,
        )
        if not linked:
            return render_login_page(
                auth_error="Unable to link Telegram account. Please try again from the mini app.",
                auth_login_input=login_value,
            ), 500

        if not set_student_session(student, telegram_user_id):
            return render_login_page(
                auth_error="Unable to initialize student session.",
                auth_login_input=login_value,
            ), 500
        return redirect(
            build_dashboard_url(
                student["sheet_student_id"],
                school=student.get("school_code", ""),
            )
        )

    @app.post("/profile/password")
    def profile_change_password():
        if current_auth_role() != "student":
            return redirect(url_for("home"))

        student_db_id = current_student_db_id()
        student_sheet_id = current_student_sheet_id()
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
                build_dashboard_url(
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
                build_dashboard_url(
                    student_sheet_id,
                    subject=subject,
                    group=group,
                    profile_error=update_error or "Unable to change password.",
                )
            )

        return redirect(
            build_dashboard_url(
                student_sheet_id,
                subject=subject,
                group=group,
                profile_notice="Password changed successfully.",
            )
        )

    @app.post("/logout")
    def logout():
        if current_auth_role() == "student":
            student_db_id = current_student_db_id()
            if student_db_id is not None:
                unlink_student_telegram_user(student_db_id)
        session.clear()
        return redirect(url_for("home", logged_out=1))

    @app.post("/search")
    def search_student_form():
        if current_auth_role() != "student":
            return redirect(url_for("home"))

        form_data = {
            "student_id": request.form.get("student_id", "").strip(),
            "group": request.form.get("group", "").strip(),
            "subject": request.form.get("subject", "").strip(),
        }

        if not is_full_form(form_data):
            return render_student_panel(
                form_data=form_data,
                panel_error="Please fill all fields.",
            ), 400

        try:
            requested_student_id = int(form_data["student_id"])
        except ValueError:
            return render_student_panel(
                form_data=form_data,
                panel_error="Please choose a valid student from the list.",
            ), 400

        school_code = _current_student_school_code()
        group_cache_entry, cache_error = get_group_cache_entry(
            form_data["subject"],
            form_data["group"],
            school_code=school_code,
        )
        if group_cache_entry and requested_student_id in group_cache_entry.get(
            "dashboards_by_id", {}
        ):
            route_params = {
                "student_id": requested_student_id,
                "subject": form_data["subject"],
                "group": form_data["group"],
            }
            if school_code:
                route_params["school"] = school_code
            return redirect(url_for("dashboard", **route_params))

        if school_code:
            dataset, load_error = load_dataset(school_code=school_code)
        else:
            dataset, load_error = load_dataset()
        if load_error or not dataset:
            return render_student_panel(
                form_data=form_data,
                panel_error=load_error
                or cache_error
                or "Unable to load Google Sheets data.",
            ), 503

        return render_student_panel(
            form_data=form_data,
            panel_error="Student not found. Please check your details.",
        ), 404

    @app.get("/api/metadata")
    def api_metadata():
        school_code = _current_student_school_code()
        if school_code:
            dataset, load_error = load_dataset(school_code=school_code)
        else:
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
        surname = request.args.get("surname", "").strip()
        name = request.args.get("name", "").strip()
        group = request.args.get("group", "").strip()
        subject = request.args.get("subject", "").strip()

        if not all([surname, name, group, subject]):
            return jsonify({"message": "All fields are required."}), 400

        school_code = _current_student_school_code()
        if school_code:
            dataset, load_error = load_dataset(school_code=school_code)
        else:
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
