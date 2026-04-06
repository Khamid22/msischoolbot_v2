from flask import render_template, request, url_for

from app.routes.students.services import payload_service


def register_rating_board_routes(
    students,
    *,
    load_dashboard_payload,
    collect_subject_dashboards_from_dataset,
    collect_subject_dashboards_from_cache,
    load_dataset,
    seed_group_cache_from_dataset,
    build_subject_leaderboard,
):
    def _should_force_refresh():
        return False

    def _normalize_text(value):
        return str(value or "").strip().casefold()

    def _filter_dashboards_for_school(dashboards, school_code, school_name):
        normalized_school_code = _normalize_text(school_code)
        normalized_school_name = _normalize_text(school_name)
        if not normalized_school_code and not normalized_school_name:
            return dashboards

        filtered_dashboards = []
        for dashboard_payload in dashboards:
            student = dashboard_payload.get("student", {})
            if not isinstance(student, dict):
                continue

            dashboard_school_code = _normalize_text(student.get("schoolCode", ""))
            dashboard_school_name = _normalize_text(student.get("schoolName", ""))
            if normalized_school_code and dashboard_school_code == normalized_school_code:
                filtered_dashboards.append(dashboard_payload)
                continue
            if normalized_school_name and dashboard_school_name == normalized_school_name:
                filtered_dashboards.append(dashboard_payload)

        return filtered_dashboards

    @students.get("/dashboard/<int:student_id>/rating-board")
    def rating_board(student_id):
        requested_subject = request.args.get("subject", "").strip()
        requested_group = request.args.get("group", "").strip()
        requested_school = request.args.get("school", "").strip()
        requested_scope = request.args.get("scope", "").strip().lower()
        force_refresh = _should_force_refresh()

        payload, dataset, error_message, status_code = payload_service.load_student_payload_for_view(
            student_id=student_id,
            requested_subject=requested_subject,
            requested_group=requested_group,
            requested_school=requested_school,
            force_refresh=force_refresh,
            load_dashboard_payload=load_dashboard_payload,
            missing_message=(
                "We could not retrieve data for this student. Please search again."
            ),
            session_invalid_message="Student session is invalid. Please login again.",
            forbidden_message="Access denied: you can open only your own rating board.",
        )
        if error_message:
            return (
                render_template(
                    "student/not_found.html",
                    message=error_message,
                ),
                status_code,
            )

        student = payload.get("student", {})
        if not isinstance(student, dict):
            return (
                render_template(
                    "student/not_found.html",
                    message="Student profile is unavailable.",
                ),
                404,
            )

        subject_name = str(student.get("subject", "")).strip()
        school_code = str(student.get("schoolCode", "")).strip() or requested_school
        school_name = str(student.get("schoolName", "")).strip()
        rating_scope = "local" if requested_scope == "local" else "global"
        dashboards = (
            collect_subject_dashboards_from_dataset(dataset, subject_name)
            if dataset
            else collect_subject_dashboards_from_cache(subject_name)
        )
        if not dashboards:
            if school_code:
                refreshed_dataset, load_error = load_dataset(
                    school_code=school_code,
                    force_refresh=force_refresh,
                )
            else:
                refreshed_dataset, load_error = load_dataset(
                    force_refresh=force_refresh,
                )
            if load_error or not refreshed_dataset:
                return (
                    render_template(
                        "student/not_found.html",
                        message=load_error or "Unable to load subject rating board.",
                    ),
                    503,
                )
            seed_group_cache_from_dataset(refreshed_dataset)
            dashboards = collect_subject_dashboards_from_dataset(
                refreshed_dataset,
                subject_name,
            )

        scoped_dashboards = dashboards
        if rating_scope == "local":
            scoped_dashboards = _filter_dashboards_for_school(
                dashboards,
                school_code,
                school_name,
            )

        leaderboard = build_subject_leaderboard(scoped_dashboards)
        current_rating = next(
            (row for row in leaderboard if row.get("studentId") == student_id),
            None,
        )
        back_url = url_for(
            "student.dashboard",
            student_id=student_id,
            subject=requested_subject or subject_name,
            group=requested_group or str(student.get("group", "")).strip(),
            school=school_code,
        )
        scope_options = []
        for scope_code, scope_label in (("local", "Local"), ("global", "Global")):
            scope_options.append(
                {
                    "code": scope_code,
                    "label": scope_label,
                    "is_current": scope_code == rating_scope,
                    "url": url_for(
                        "student.rating_board",
                        student_id=student_id,
                        subject=requested_subject or subject_name,
                        group=requested_group or str(student.get("group", "")).strip(),
                        school=school_code,
                        scope=scope_code,
                    ),
                }
            )
        rating_scope_label = (
            f"{school_name or school_code or 'Current school'} only"
            if rating_scope == "local"
            else "All schools"
        )

        return render_template(
            "student/rating_board.html",
            current_student=student,
            current_student_id=student_id,
            current_rating=current_rating,
            leaderboard=leaderboard,
            subject_name=subject_name,
            back_url=back_url,
            rating_scope=rating_scope,
            rating_scope_label=rating_scope_label,
            scope_options=scope_options,
        )
