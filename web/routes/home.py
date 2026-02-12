from flask import jsonify, redirect, render_template, request, session, url_for

try:
    from ..auth_store import (
        detect_login_role,
        get_bot_users_count,
        init_storage,
        list_students_for_admin,
        sync_students_if_needed,
        verify_admin_credentials,
        verify_student_credentials,
    )
except ImportError:
    from auth_store import (
        detect_login_role,
        get_bot_users_count,
        init_storage,
        list_students_for_admin,
        sync_students_if_needed,
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
        )

    def _render_admin_page(auth_error=""):
        sync_result = sync_students_if_needed(load_dataset)
        sync_error = str(sync_result.get("error", "")).strip()

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
        )

    # Home page now works as auth entry + role-based panel.
    @app.get("/")
    def home():
        role = _current_auth_role()

        if role == "admin":
            return _render_admin_page()

        if role == "student":
            own_sheet_student_id = _current_student_sheet_id()
            if own_sheet_student_id is None:
                session.clear()
                return _render_login_page(
                    auth_error="Student session is invalid. Please login again.",
                ), 401
            return redirect(url_for("dashboard", student_id=own_sheet_student_id))

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

            session.clear()
            session["auth_role"] = "admin"
            session["auth_login"] = admin["login"]
            session["admin_id"] = admin["id"]
            session["admin_is_owner"] = bool(admin.get("is_owner"))
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

        session.clear()
        session["auth_role"] = "student"
        session["auth_login"] = student["student_id"]
        session["student_db_id"] = student["id"]
        session["student_id"] = student["student_id"]
        session["student_sheet_id"] = student["sheet_student_id"]
        session["student_full_name"] = student["full_name"]
        return redirect(
            url_for(
                "dashboard",
                student_id=student["sheet_student_id"],
            )
        )

    @app.post("/logout")
    def logout():
        session.clear()
        return redirect(url_for("home"))

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
