from datetime import datetime, timezone

from backend.utils.response_helpers import jsonify
from backend.utils.context import request
from backend.utils.session import url_for
from backend.render import generate_csrf

from backend.render import render_react_page
from backend.domains.announcements.service import list_announcements
from backend.utils.performance import PagePerformanceTimer, log_page_performance

from backend.roles.student.services import (
    dashboard_service,
    payload_service,
)


def register_dashboard_routes(students):
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

    def _student_announcements():
        try:
            announcements = list_announcements(include_drafts=False)
        except Exception:
            return []
        allowed_audiences = {"all", "students"}
        visible = []
        for item in announcements:
            audience = str(item.get("audience") or "").strip().casefold()
            if audience not in allowed_audiences:
                continue
            visible.append(
                {
                    "id": item.get("id"),
                    "title": item.get("title", ""),
                    "body": item.get("body", ""),
                    "priority": item.get("priority", "info"),
                    "pinned": bool(item.get("pinned")),
                    "publishedAt": item.get("publishedAt") or item.get("updatedAt") or "",
                }
            )
            if len(visible) >= 3:
                break
        return visible

    @students.get("/dashboard/{student_id}")
    def dashboard(student_id: int):
        timer = PagePerformanceTimer()
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
            missing_message=(
                "We could not retrieve data for this student. Please search again."
            ),
            session_invalid_message="Student session is invalid. Please login again.",
            forbidden_message="Access denied: you can open only your own dashboard.",
        )
        timer.mark("payload_load")

        if error_message:
            response = render_react_page(
                    "student-not-found",
                    {"message": error_message, "returnUrl": url_for("student.home")},
                    title="Student Not Found", status_code=status_code)
            timer.mark("render")
            log_page_performance(
                "student_dashboard_error",
                timer,
                response=response,
                rows={},
            )
            return response

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
            force_refresh=force_refresh,
        )
        timer.mark("context_build")

        payload_student = payload.get("student", {}) if isinstance(payload, dict) else {}
        school_code = str(payload_student.get("schoolCode", "")).strip() or requested_school
        last_updated_at_value = None

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
        context["last_updated_label"] = _format_last_updated_label(last_updated_at_value)

        current_subject = context["current_subject_name"]
        current_group = str(payload_student.get("group", "")).strip()
        chat_url = url_for(
            "student.chat_room",
            student_id=student_id,
            subject=requested_subject or current_subject,
            group=requested_group or current_group,
            school=school_code,
        )
        office_hours_url = url_for(
            "student.student_office_hours",
            student_id=student_id,
            subject=requested_subject or current_subject,
            group=requested_group or current_group,
            school=school_code,
        )

        announcements = _student_announcements()
        timer.mark("announcements")

        response = render_react_page(
            "student-dashboard",
            {
                "payload": context["payload"],
                "attendanceRate": context["attendance_rate"],
                "examPerformance": context["exam_performance"],
                "programCompletedLessons": context["program_completed_lessons"],
                "programCompletedRate": context["program_completed_rate"],
                "ratingBoardUrl": context["rating_board_url"],
                "resourcesUrl": context["resources_url"],
                "chatUrl": chat_url,
                "officeHoursUrl": office_hours_url,
                "aapLessonsUrl": context["aap_lessons_url"],
                "arLessonsUrl": context["ar_lessons_url"],
                "currentSubjectName": context["current_subject_name"],
                "currentSubjectShortName": context["current_subject_short_name"],
                "subjectSwitchOptions": context["subject_switch_options"],
                "studentProfile": context["student_profile"],
                "profileNotice": context["profile_notice"],
                "profileError": context["profile_error"],
                "dashboardBackUrl": context["dashboard_back_url"],
                "showDashboardBack": context.get("show_dashboard_back", False),
                "refreshUrl": context.get("refresh_url", ""),
                "lastUpdatedLabel": context.get("last_updated_label", ""),
                "lastUpdatedAt": last_updated_at_value,
                "announcements": announcements,
                "csrfToken": generate_csrf(),
                "logoutUrl": url_for("student.logout"),
                "changePasswordUrl": url_for("student.profile_change_password"),
                "embedMode": request.args.get("embed", "").strip(),
            },
            title="Academic Dashboard",
            description="Mobile-optimized MSI School dashboard with attendance and performance charts.",
            back_mode="history",
            back_url=context.get("dashboard_back_url"),
        )
        timer.mark("render")
        log_page_performance(
            "student_dashboard",
            timer,
            response=response,
            rows={
                "subject_switch_options": context["subject_switch_options"],
                "announcements": announcements,
                "payload_keys": context["payload"] if isinstance(context["payload"], dict) else {},
            },
        )
        return response

    @students.get("/dashboard/{student_id}/aap-lessons")
    def aap_lessons(student_id: int):
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
            missing_message=(
                "We could not retrieve data for this student. Please search again."
            ),
            session_invalid_message="Student session is invalid. Please login again.",
            forbidden_message="Access denied: you can open only your own AAP table.",
        )
        if error_message:
            return render_react_page(
                    "student-not-found",
                    {"message": error_message, "returnUrl": url_for("student.home")},
                    title="Student Not Found", status_code=status_code)

        context, build_error, build_status_code = dashboard_service.build_aap_lessons_page_context(
            student_id=student_id,
            payload=payload,
            requested_subject=requested_subject,
            requested_group=requested_group,
            requested_school=requested_school,
            force_refresh=force_refresh,
        )
        if build_error:
            return render_react_page(
                    "student-not-found",
                    {"message": build_error, "returnUrl": url_for("student.home")},
                    title="Student Not Found", status_code=build_status_code)

        return render_react_page(
            "student-aap",
            {
                "backUrl": context["back_url"],
                "studentFullName": context["student_full_name"],
                "subjectName": context["subject_name"],
                "lessonRows": context["lesson_rows"],
                "embedMode": request.args.get("embed", "").strip(),
            },
            title="AAP Lesson Mastery",
            description="Average Academic Performance by lesson.",
            back_mode="history",
            back_url=context.get("back_url"),
        )

    @students.get("/dashboard/{student_id}/ar-lessons")
    def ar_lessons(student_id: int):
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
            missing_message=(
                "We could not retrieve data for this student. Please search again."
            ),
            session_invalid_message="Student session is invalid. Please login again.",
            forbidden_message="Access denied: you can open only your own AR table.",
        )
        if error_message:
            return render_react_page(
                    "student-not-found",
                    {"message": error_message, "returnUrl": url_for("student.home")},
                    title="Student Not Found", status_code=status_code)

        context, build_error, build_status_code = dashboard_service.build_ar_lessons_page_context(
            student_id=student_id,
            payload=payload,
            requested_subject=requested_subject,
            requested_group=requested_group,
            requested_school=requested_school,
            force_refresh=force_refresh,
        )
        if build_error:
            return render_react_page(
                    "student-not-found",
                    {"message": build_error, "returnUrl": url_for("student.home")},
                    title="Student Not Found", status_code=build_status_code)

        return render_react_page(
            "student-ar",
            {
                "backUrl": context["back_url"],
                "studentFullName": context["student_full_name"],
                "subjectName": context["subject_name"],
                "lessonRows": context["lesson_rows"],
                "embedMode": request.args.get("embed", "").strip(),
            },
            title="Attendance By Lesson",
            description="Attendance record by lesson.",
            back_mode="history",
            back_url=context.get("back_url"),
        )

    @students.get("/api/students/{student_id}/dashboard")
    def api_student_dashboard(student_id: int):
        requested_school = request.args.get("school", "").strip()
        force_refresh = should_force_refresh()

        payload, _dataset, error_message, status_code = payload_service.load_student_payload_for_view(
            student_id=student_id,
            requested_subject="",
            requested_group="",
            requested_school=requested_school,
            force_refresh=force_refresh,
            missing_message="Student not found",
            session_invalid_message="Student session is invalid.",
            forbidden_message="Access denied.",
        )
        if error_message:
            return jsonify({"message": error_message}, status_code=status_code)

        return jsonify(payload)
