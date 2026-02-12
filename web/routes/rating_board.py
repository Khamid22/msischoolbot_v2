from flask import render_template, request, session, url_for


def register_rating_board_routes(
    app,
    *,
    load_dashboard_payload,
    collect_subject_dashboards_from_dataset,
    collect_subject_dashboards_from_cache,
    load_dataset,
    seed_group_cache_from_dataset,
    build_subject_leaderboard,
):
    def _normalize_text(value):
        return " ".join(str(value or "").strip().casefold().split())

    def _current_auth_role():
        return str(session.get("auth_role", "")).strip().lower()

    def _current_student_sheet_id():
        raw_value = session.get("student_sheet_id")
        try:
            return int(raw_value)
        except (TypeError, ValueError):
            return None

    def _current_student_full_name():
        return str(session.get("student_full_name", "")).strip()

    def _is_student_owner_of_payload(student_id, payload):
        own_full_name = _normalize_text(_current_student_full_name())
        if own_full_name:
            payload_student = payload.get("student", {}) if isinstance(payload, dict) else {}
            payload_full_name = _normalize_text(payload_student.get("fullName", ""))
            return bool(payload_full_name) and payload_full_name == own_full_name

        own_sheet_student_id = _current_student_sheet_id()
        return own_sheet_student_id is not None and int(student_id) == own_sheet_student_id

    # Subject leaderboard page for the current student's subject.
    @app.get("/dashboard/<int:student_id>/rating-board")
    def rating_board(student_id):
        requested_subject = request.args.get("subject", "").strip()
        requested_group = request.args.get("group", "").strip()

        payload, dataset, payload_error = load_dashboard_payload(
            student_id=student_id,
            requested_subject=requested_subject,
            requested_group=requested_group,
        )
        if payload_error:
            return (
                render_template(
                    "not_found.html",
                    message=payload_error,
                ),
                503,
            )

        if not payload:
            return (
                render_template(
                    "not_found.html",
                    message="We could not retrieve data for this student. Please search again.",
                ),
                404,
            )

        if _current_auth_role() == "student" and not _is_student_owner_of_payload(
            student_id, payload
        ):
            if not _current_student_sheet_id() and not _current_student_full_name():
                return (
                    render_template(
                        "not_found.html",
                        message="Student session is invalid. Please login again.",
                    ),
                    401,
                )
            return (
                render_template(
                    "not_found.html",
                    message="Access denied: you can open only your own rating board.",
                ),
                403,
            )

        student = payload.get("student", {})
        if not isinstance(student, dict):
            return (
                render_template(
                    "not_found.html",
                    message="Student profile is unavailable.",
                ),
                404,
            )

        subject_name = str(student.get("subject", "")).strip()
        dashboards = (
            collect_subject_dashboards_from_dataset(dataset, subject_name)
            if dataset
            else collect_subject_dashboards_from_cache(subject_name)
        )
        if not dashboards:
            refreshed_dataset, load_error = load_dataset()
            if load_error or not refreshed_dataset:
                return (
                    render_template(
                        "not_found.html",
                        message=load_error or "Unable to load subject rating board.",
                    ),
                    503,
                )
            seed_group_cache_from_dataset(refreshed_dataset)
            dashboards = collect_subject_dashboards_from_dataset(
                refreshed_dataset,
                subject_name,
            )

        leaderboard = build_subject_leaderboard(dashboards)
        current_rating = next(
            (row for row in leaderboard if row.get("studentId") == student_id),
            None,
        )
        back_url = url_for(
            "dashboard",
            student_id=student_id,
            subject=requested_subject or subject_name,
            group=requested_group or str(student.get("group", "")).strip(),
        )

        return render_template(
            "rating_board.html",
            current_student=student,
            current_student_id=student_id,
            current_rating=current_rating,
            leaderboard=leaderboard,
            subject_name=subject_name,
            back_url=back_url,
        )
