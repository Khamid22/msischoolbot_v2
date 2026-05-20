from flask import Blueprint, jsonify, request, session, url_for
from flask_wtf.csrf import generate_csrf

from app.web.render import render_react_page

from app.routes.user_auth import register_user_auth_routes
from app.routes.students.dashboard import register_dashboard_routes
from app.routes.students.rating_board import register_rating_board_routes
from app.routes.students.chat_page import register_chat_page_routes
from app.routes.students.chat_routes import register_chat_routes
from app.routes.students.comment_routes import register_comment_routes
from app.routes.students.resources import register_resources_routes
from app.routes.students.services.auth_service import (
    get_student_db_id_by_sheet_student_id,
    record_student_activity,
)
from app.routes.students.services.page_service import build_student_panel_context
from app.routes.students.services.session_state_service import (
    current_auth_login,
    current_auth_role,
    current_student_db_id,
    current_student_school_code,
    current_student_sheet_id,
)
from app.routes.students.students import register_student_routes


def register_student_page_routes(
    app,
    *,
    render_admin_page,
    load_dataset,
    seed_group_cache_from_dataset,
    build_students_by_subject_group,
    is_full_form,
    get_group_cache_entry,
    search_student,
    load_dashboard_payload,
    collect_subject_dashboards_from_dataset,
    collect_subject_dashboards_from_cache,
    extract_attendance_rate,
    extract_exam_average_score,
    round_grade_half_up,
    compute_subject_rating,
    build_subject_leaderboard,
):
    def should_force_refresh():
        return False

    def render_login_page(auth_error="", auth_login_input=""):
        return render_react_page(
            "login",
            {
                "authError": auth_error,
                "authLoginInput": auth_login_input,
                "submitUrl": url_for("student.login"),
                "csrfToken": generate_csrf(),
            },
            title="MSI School Portal",
            description="Login to continue.",
        )

    def render_student_panel(form_data, panel_error=""):
        context = build_student_panel_context(
            form_data=form_data,
            student_school_code=current_student_school_code(),
            load_dataset=load_dataset,
            seed_group_cache_from_dataset=seed_group_cache_from_dataset,
            build_students_by_subject_group=build_students_by_subject_group,
            force_refresh=should_force_refresh(),
        )

        return render_react_page(
            "student-home",
            {
                "subjects": context["subjects"],
                "groupsBySubject": context["groups_by_subject"],
                "studentsBySubjectGroup": context["students_by_subject_group"],
                "formData": context["form_data"],
                "error": panel_error or context["load_error"] or "",
                "authLogin": current_auth_login(),
                "csrfToken": generate_csrf(),
                "logoutUrl": url_for("student.logout"),
                "searchUrl": url_for("student.search_student_form"),
            },
            title="MSI School Portal",
            description="Select stream, group, and student.",
        )

    students = Blueprint("student", __name__)

    @students.before_request
    def track_student_activity():
        if request.endpoint == "student.activity_ping":
            return None
        if current_auth_role() != "student":
            return None
        student_db_id = current_student_db_id()
        if student_db_id is not None:
            record_student_activity(student_db_id)
        return None

    @students.get("/api/activity/ping")
    def activity_ping():
        if current_auth_role() != "student":
            return jsonify({"ok": False, "message": "Student session is missing."}), 401

        student_db_id = current_student_db_id()
        if student_db_id is None:
            return jsonify({"ok": False, "message": "Student session is missing."}), 401

        result = record_student_activity(student_db_id)
        if result.get("reason") == "student_not_found":
            sheet_student_id = current_student_sheet_id()
            school_code = current_student_school_code()
            resolved_student_db_id = get_student_db_id_by_sheet_student_id(
                sheet_student_id,
                school_code=school_code,
            )
            if resolved_student_db_id and resolved_student_db_id != student_db_id:
                session["student_db_id"] = resolved_student_db_id
                result = record_student_activity(resolved_student_db_id)

        if result.get("updated") or result.get("skipped"):
            return jsonify({"ok": True, **result})

        status_code = 404 if result.get("reason") == "student_not_found" else 500
        return jsonify({"ok": False, **result}), status_code

    register_user_auth_routes(
        students,
        render_login_page=render_login_page,
        render_admin_page=render_admin_page,
    )
    register_student_routes(
        students,
        load_dataset=load_dataset,
        is_full_form=is_full_form,
        render_student_panel=render_student_panel,
        get_group_cache_entry=get_group_cache_entry,
        build_students_by_subject_group=build_students_by_subject_group,
        search_student=search_student,
    )
    register_dashboard_routes(
        students,
        load_dashboard_payload=load_dashboard_payload,
        load_dataset=load_dataset,
        extract_attendance_rate=extract_attendance_rate,
        extract_exam_average_score=extract_exam_average_score,
        round_grade_half_up=round_grade_half_up,
        compute_subject_rating=compute_subject_rating,
    )
    register_rating_board_routes(
        students,
        load_dashboard_payload=load_dashboard_payload,
        collect_subject_dashboards_from_dataset=collect_subject_dashboards_from_dataset,
        collect_subject_dashboards_from_cache=collect_subject_dashboards_from_cache,
        load_dataset=load_dataset,
        seed_group_cache_from_dataset=seed_group_cache_from_dataset,
        build_subject_leaderboard=build_subject_leaderboard,
    )
    register_resources_routes(
        students,
        load_dashboard_payload=load_dashboard_payload,
    )
    register_comment_routes(students)
    register_chat_page_routes(students, load_dashboard_payload=load_dashboard_payload)
    register_chat_routes(students)
    app.register_blueprint(students)
