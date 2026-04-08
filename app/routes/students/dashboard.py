from datetime import datetime, timezone

from flask import jsonify, render_template, request, url_for

from app.integrations.sheets_data import get_school_dataset_last_updated

from app.routes.students.services import (
    dashboard_service,
    payload_service,
)


def register_dashboard_routes(
    students,
    *,
    load_dashboard_payload,
    load_dataset,
    extract_attendance_rate,
    extract_exam_average_score,
    round_grade_half_up,
    compute_subject_rating,
):
    def _is_refresh_requested():
        refresh_value = str(request.args.get("refresh", "")).strip().casefold()
        return refresh_value in {"1", "true", "yes", "y", "on"}

    def _format_last_updated_label(last_updated_at):
        def _format_relative_age(seconds_elapsed):
            units = (
                (31536000, "year"),
                (2592000, "month"),
                (604800, "week"),
                (86400, "day"),
                (3600, "hour"),
                (60, "minute"),
            )
            for unit_seconds, unit_name in units:
                if seconds_elapsed >= unit_seconds:
                    amount = seconds_elapsed // unit_seconds
                    suffix = "" if amount == 1 else "s"
                    return f"{amount} {unit_name}{suffix} ago"
            return "moments ago"

        if last_updated_at is None:
            return "Last Update: --."
        try:
            timestamp = float(last_updated_at)
        except (TypeError, ValueError):
            return "Last Update: --."
        if timestamp <= 0:
            return "Last Update: --."

        updated_at_utc = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        now_utc = datetime.now(timezone.utc)
        seconds_elapsed = max(0, int((now_utc - updated_at_utc).total_seconds()))
        return "Last Update: " + _format_relative_age(seconds_elapsed) + "."

    def should_force_refresh():
        return _is_refresh_requested()

    @students.get("/dashboard/<int:student_id>")
    def dashboard(student_id):
        requested_subject = request.args.get("subject", "").strip()
        requested_group = request.args.get("group", "").strip()
        requested_school = request.args.get("school", "").strip()
        admin_return_panel = request.args.get("admin_return_panel", "").strip().lower()
        admin_return_school = request.args.get("admin_return_school", "").strip().lower()
        profile_notice = request.args.get("profile_notice", "").strip()
        profile_error = request.args.get("profile_error", "").strip()
        force_refresh = should_force_refresh()

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
            forbidden_message="Access denied: you can open only your own dashboard.",
        )

        if error_message:
            return (
                render_template(
                    "student/not_found.html",
                    message=error_message,
                ),
                status_code,
            )

        context = dashboard_service.build_dashboard_page_context(
            student_id=student_id,
            payload=payload,
            dataset=dataset,
            requested_subject=requested_subject,
            requested_group=requested_group,
            requested_school=requested_school,
            admin_return_panel=admin_return_panel,
            admin_return_school=admin_return_school,
            profile_notice=profile_notice,
            profile_error=profile_error,
            load_dataset=load_dataset,
            extract_attendance_rate=extract_attendance_rate,
            extract_exam_average_score=extract_exam_average_score,
            round_grade_half_up=round_grade_half_up,
            compute_subject_rating=compute_subject_rating,
            force_refresh=force_refresh,
        )

        payload_student = payload.get("student", {}) if isinstance(payload, dict) else {}
        school_code = str(payload_student.get("schoolCode", "")).strip() or requested_school
        last_updated_at = get_school_dataset_last_updated(school_code=school_code)

        refresh_subject = requested_subject or str(payload_student.get("subject", "")).strip()
        refresh_group = requested_group or str(payload_student.get("group", "")).strip()
        refresh_params = {
            "student_id": student_id,
            "refresh": "1",
        }
        if refresh_subject:
            refresh_params["subject"] = refresh_subject
        if refresh_group:
            refresh_params["group"] = refresh_group
        if school_code:
            refresh_params["school"] = school_code
        if admin_return_panel:
            refresh_params["admin_return_panel"] = admin_return_panel
        if admin_return_school:
            refresh_params["admin_return_school"] = admin_return_school

        context["refresh_url"] = url_for("student.dashboard", **refresh_params)
        context["last_updated_label"] = _format_last_updated_label(last_updated_at)

        return render_template("student/dashboard.html", **context)

    @students.get("/dashboard/<int:student_id>/aap-lessons")
    def aap_lessons(student_id):
        requested_subject = request.args.get("subject", "").strip()
        requested_group = request.args.get("group", "").strip()
        requested_school = request.args.get("school", "").strip()
        force_refresh = should_force_refresh()

        payload, _dataset, error_message, status_code = payload_service.load_student_payload_for_view(
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
            forbidden_message="Access denied: you can open only your own AAP table.",
        )
        if error_message:
            return (
                render_template(
                    "student/not_found.html",
                    message=error_message,
                ),
                status_code,
            )

        context, build_error, build_status_code = dashboard_service.build_aap_lessons_page_context(
            student_id=student_id,
            payload=payload,
            requested_subject=requested_subject,
            requested_group=requested_group,
            requested_school=requested_school,
            load_dataset=load_dataset,
            round_grade_half_up=round_grade_half_up,
            force_refresh=force_refresh,
        )
        if build_error:
            return (
                render_template(
                    "student/not_found.html",
                    message=build_error,
                ),
                build_status_code,
            )

        return render_template("student/aap_lessons.html", **context)

    @students.get("/dashboard/<int:student_id>/ar-lessons")
    def ar_lessons(student_id):
        requested_subject = request.args.get("subject", "").strip()
        requested_group = request.args.get("group", "").strip()
        requested_school = request.args.get("school", "").strip()
        force_refresh = should_force_refresh()

        payload, _dataset, error_message, status_code = payload_service.load_student_payload_for_view(
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
            forbidden_message="Access denied: you can open only your own AR table.",
        )
        if error_message:
            return (
                render_template(
                    "student/not_found.html",
                    message=error_message,
                ),
                status_code,
            )

        context, build_error, build_status_code = dashboard_service.build_ar_lessons_page_context(
            student_id=student_id,
            payload=payload,
            requested_subject=requested_subject,
            requested_group=requested_group,
            requested_school=requested_school,
            load_dataset=load_dataset,
            force_refresh=force_refresh,
        )
        if build_error:
            return (
                render_template(
                    "student/not_found.html",
                    message=build_error,
                ),
                build_status_code,
            )

        return render_template("student/ar_lessons.html", **context)

    @students.get("/api/students/<int:student_id>/dashboard")
    def api_student_dashboard(student_id):
        requested_school = request.args.get("school", "").strip()
        force_refresh = should_force_refresh()

        payload, _dataset, error_message, status_code = payload_service.load_student_payload_for_view(
            student_id=student_id,
            requested_subject="",
            requested_group="",
            requested_school=requested_school,
            force_refresh=force_refresh,
            load_dashboard_payload=load_dashboard_payload,
            missing_message="Student not found",
            session_invalid_message="Student session is invalid.",
            forbidden_message="Access denied.",
        )
        if error_message:
            return jsonify({"message": error_message}), status_code

        return jsonify(payload)
