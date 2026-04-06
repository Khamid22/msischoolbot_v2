from flask import render_template, request, url_for

from app.config.schools import get_configured_school_spreadsheets
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

    def _dashboard_cache_key(dashboard_payload):
        student = dashboard_payload.get("student", {})
        if not isinstance(student, dict):
            return None

        student_id = student.get("id")
        return (
            _normalize_text(student.get("schoolCode", "")),
            _normalize_text(student.get("schoolName", "")),
            int(student_id) if isinstance(student_id, int) else _normalize_text(student_id),
            _normalize_text(student.get("fullName", "")),
            _normalize_text(student.get("group", "")),
        )

    def _extend_unique_dashboards(target_dashboards, seen_keys, dashboards):
        for dashboard_payload in dashboards:
            cache_key = _dashboard_cache_key(dashboard_payload)
            if cache_key is not None and cache_key in seen_keys:
                continue
            if cache_key is not None:
                seen_keys.add(cache_key)
            target_dashboards.append(dashboard_payload)

    def _load_subject_dashboards_for_school(subject_name, school_code, force_refresh):
        normalized_school_code = str(school_code or "").strip()
        if normalized_school_code:
            dataset, load_error = load_dataset(
                school_code=normalized_school_code,
                force_refresh=force_refresh,
            )
        else:
            dataset, load_error = load_dataset(force_refresh=force_refresh)
        if load_error or not dataset:
            return [], load_error or "Unable to load subject rating board."

        seed_group_cache_from_dataset(dataset)
        return collect_subject_dashboards_from_dataset(dataset, subject_name), None

    def _load_subject_dashboards_across_schools(
        subject_name,
        *,
        primary_dataset=None,
        primary_school_code="",
        force_refresh=False,
    ):
        dashboards = []
        seen_keys = set()
        first_load_error = ""

        if primary_dataset:
            _extend_unique_dashboards(
                dashboards,
                seen_keys,
                collect_subject_dashboards_from_dataset(primary_dataset, subject_name),
            )

        configured_school_codes = list(get_configured_school_spreadsheets().keys())
        if not configured_school_codes:
            configured_school_codes = [str(primary_school_code or "").strip()]

        normalized_primary_school_code = _normalize_text(primary_school_code)
        for school_code in configured_school_codes:
            normalized_school_code = _normalize_text(school_code)
            if primary_dataset and normalized_school_code == normalized_primary_school_code:
                continue

            if normalized_school_code:
                dataset, load_error = load_dataset(
                    school_code=normalized_school_code,
                    force_refresh=force_refresh,
                )
            else:
                dataset, load_error = load_dataset(force_refresh=force_refresh)
            if load_error or not dataset:
                if load_error and not first_load_error:
                    first_load_error = load_error
                continue

            seed_group_cache_from_dataset(dataset)
            _extend_unique_dashboards(
                dashboards,
                seen_keys,
                collect_subject_dashboards_from_dataset(dataset, subject_name),
            )

        if dashboards:
            return dashboards, None

        cached_dashboards = []
        _extend_unique_dashboards(
            cached_dashboards,
            set(),
            collect_subject_dashboards_from_cache(subject_name),
        )
        if cached_dashboards:
            return cached_dashboards, None

        return [], first_load_error or "Unable to load subject rating board."

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
        load_error = ""
        if rating_scope == "global":
            dashboards, load_error = _load_subject_dashboards_across_schools(
                subject_name,
                primary_dataset=dataset,
                primary_school_code=school_code,
                force_refresh=force_refresh,
            )
        else:
            dashboards = (
                collect_subject_dashboards_from_dataset(dataset, subject_name)
                if dataset
                else []
            )
            if not dashboards:
                dashboards, load_error = _load_subject_dashboards_for_school(
                    subject_name,
                    school_code,
                    force_refresh,
                )
            dashboards = _filter_dashboards_for_school(
                dashboards,
                school_code,
                school_name,
            )

        if load_error and not dashboards:
            return (
                render_template(
                    "student/not_found.html",
                    message=load_error or "Unable to load subject rating board.",
                ),
                503,
            )

        leaderboard = build_subject_leaderboard(dashboards)
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
