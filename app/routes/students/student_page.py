from flask import Blueprint, render_template

from app.routes.user_auth import register_user_auth_routes
from app.routes.students.dashboard import register_dashboard_routes
from app.routes.students.rating_board import register_rating_board_routes
from app.routes.students.resources import register_resources_routes
from app.routes.students.services.page_service import build_student_panel_context
from app.routes.students.services.session_state_service import (
    current_auth_login,
    current_student_school_code,
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
        return render_template(
            "auth/login.html",
            error="",
            auth_error=auth_error,
            auth_login_input=auth_login_input,
            admin_notice="",
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

        return render_template(
            "student/home.html",
            groups=context["groups"],
            groups_by_subject=context["groups_by_subject"],
            subjects=context["subjects"],
            students_by_subject_group=context["students_by_subject_group"],
            error=panel_error or context["load_error"] or "",
            form_data=context["form_data"],
            auth_login=current_auth_login(),
            auth_error="",
            admin_notice="",
        )

    students = Blueprint("student", __name__)
    register_user_auth_routes(
        students,
        render_login_page=render_login_page,
        render_admin_page=render_admin_page,
        load_dataset=load_dataset,
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
    app.register_blueprint(students)
